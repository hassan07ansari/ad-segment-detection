from fastapi import FastAPI
from pydantic import BaseModel

from main import process_video


app = FastAPI()


class VideoRequest(BaseModel):
    url: str


@app.get("/")
def home():

    return {
        "message": "Ad Segment Detection API"
    }


@app.post("/detect")
def detect(request: VideoRequest):

    result = process_video(
        request.url
    )

    return result