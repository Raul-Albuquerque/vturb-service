import requests
from fastapi import FastAPI
from datetime import datetime
from app.vturb_client import get_all_player_data
from app.core.helpers import get_date_range

from app.models.report_model import ReportResponse
from config import TIMEZONE

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Olá, bem-vindo ao Neobright Solutions!"}


@app.get("/report/{day}")
def generate_report(day: str):
    url = "https://automacao-nkh9m.ondigitalocean.app/api/v1/data/players_id"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            response = requests.get(url)
            players_id_list = response.json()
        if response.status_code == 200:
            players_id_list = response.json()

        period = get_date_range(day)
        result = get_all_player_data(period=period, player_ids=players_id_list)
        return result
    except Exception as e:
        return ReportResponse(
            report_title="Vturb service - Error",
            generated_at=datetime.now(TIMEZONE),
            message=f"Error: {str(e)}",
            status=400,
        )


@app.get("/health")
async def check_health():
    return "Funcionando"
