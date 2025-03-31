import asyncio
import authentication
import models, schemas
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from config import SessionLocal, engine
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from schemas import *
from config import redis_client
import random
import string
from datetime import datetime, timedelta
import pytz
from datetime import timezone
from typing import Optional


def fetch_link(db: Session, short_code: str) -> Optional[models.Link]:
    cache = redis_client.get(f"link:{short_code}")
    if cache is not None:
        print(f'{short_code} взята из кэша')
        return db.query(models.Link).filter(models.Link.short_code == short_code).first()
    return db.query(models.Link).filter(models.Link.short_code == short_code).first()


def add_clicks(db: Session, short_code: str) -> Optional[models.Link]:
    db_link = fetch_link(db, short_code)
    if db_link:
        db_link.clicks += 1
        db_link.last_accessed = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_link)
    return db_link


def delete_links(db: Session) -> None:
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    time_end = db.query(models.Link).filter(models.Link.expires_at < now).all()
    notactive = db.query(models.Link).filter(models.Link.last_accessed < (now - timedelta(days=7))).all()
    for link in time_end + notactive:
        db.delete(link)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise


models.Base.metadata.create_all(bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def cleanup():
    while True:
        await asyncio.sleep(300)
        with SessionLocal() as db:
            delete_links(db)

@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        delete_links(db)
    task = asyncio.create_task(cleanup())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def cur_usr(token: Optional[str] = None,db: Session = Depends(get_db)) -> Optional[models.User]:
    if token is None:
        return token
    try:
        dec = jwt.decode(token, authentication.SECRET_KEY, algorithms=[authentication.ALGORITHM])
        username: str = dec.get("sub")
        if username is None:
            return None
    except (KeyError,JWTError,TypeError):
        return None
    return db.query(models.User).filter(models.User.username == username).first()


@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_exist = db.query(models.User).filter(
        (models.User.email == user.email) |
        (models.User.username == user.username)
    ).first()
    if user_exist:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = authentication.hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    return db_user


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not authentication.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось авторизоваться"
        )
    return {"token": authentication.create_token({"sub": user.username})}


@app.post("/links/shorten", response_model=schemas.Link)
def create_short_link(link: schemas.LinkCreate,db: Session = Depends(get_db),current_user: Optional[models.User] = Depends(cur_usr)):
    if not current_user:
        link.is_permanent = False
        link.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    else:
        if link.is_permanent is False:
            link.expires_at = datetime.now() + timedelta(days=1)

    if current_user is None or link.is_permanent is None:
        link.is_permanent = False
        link.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    short_code = link.custom_alias.strip() if link.custom_alias else ''.join(random.choices(string.ascii_letters, k=10))
    if db.query(models.Link).filter(models.Link.short_code == short_code).first():
        raise ValueError(f"Код '{short_code}' уже существует!")
    db_link = models.Link(
        original_url=link.original_url,
        short_code=short_code,
        created_at=datetime.now(timezone.utc),
        expires_at=link.expires_at.astimezone(timezone.utc) if link.expires_at else None,
        is_permanent=link.is_permanent,
        owner_id=current_user.id if current_user else None,
        last_accessed=datetime.now(timezone.utc),
        clicks=0
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link



@app.get("/links/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    cache = redis_client.get(f"link:{short_code}")
    if cache is not None:
        print(f'{short_code} взята из кэша')
        add_clicks(db, short_code)
        return RedirectResponse(url=redis_client.get(f"link:{short_code}"))
    link = fetch_link(db, short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    redis_client.setex(f"link:{short_code}", 3600, link.original_url)
    add_clicks(db,short_code)
    return RedirectResponse(url=link.original_url)

@app.delete("/links/{short_code}")
def delete_short_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(cur_usr)
):
    link = fetch_link(db, short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    if link.owner_id is not None and link.owner_id != current_user.id:
        raise ValueError("Нет прав")
    if link.owner_id is not None and link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы не можете удалить эту ссылку")

    db.delete(link)
    db.commit()
    redis_client.delete(f"link:{short_code}")
    return {"message": "Ссылка удалена"}


@app.put("/links/{short_code}")
def update_short_link(short_code: str,original_url: str,db: Session = Depends(get_db),current_user: models.User = Depends(cur_usr)):
    db_link = db.query(models.Link).filter(models.Link.original_url == original_url).first()
    if db_link is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    if db_link.owner_id is not None and db_link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы не можете изменить эту ссылку")

    if not db_link:
        return None
    if short_code:
        db_link.short_code = short_code
    db.commit()
    db.refresh(db_link)
    redis_client.delete(f"link:{short_code}")
    return db_link


@app.get("/links/{short_code}/stats", response_model=schemas.Link)
def get_link_stats(short_code: str, db: Session = Depends(get_db)):
    return fetch_link(db, short_code) or HTTPException(status_code=404, detail="Ссылка не найдена")

@app.get("/links/{short_code}/original")
def get_original_url(short_code: str, db: Session = Depends(get_db)):
    link = fetch_link(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    return {"original_url": link.original_url}

@app.post("/links/{short_code}/update_expiry")
def update_link_expiry(short_code: str, request_data: LinkExpiryUpdate, db: Session = Depends(get_db),
                       user: models.User = Depends(cur_usr)):
    link_entry = fetch_link(db, short_code)
    if not link_entry:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")
    if not user or link_entry.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Нет прав для изменения данной ссылки")

    new_expiry = request_data.expires_at.replace(tzinfo=None)
    link_entry.expires_at = new_expiry
    db.commit()
    db.refresh(link_entry)
    redis_client.delete(f"link:{short_code}")

    return {"message": "Дата истечения ссылки обновлена", "expires_at": new_expiry}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")