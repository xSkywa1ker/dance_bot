from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import auth, directions, slots, products, bookings, payments, users, misc
from .db.session import Base, engine


app = FastAPI(title="DanceStudioBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(directions.router, prefix="/api/v1")
app.include_router(slots.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(misc.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
