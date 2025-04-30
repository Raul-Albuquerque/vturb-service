from fastapi import FastAPI
from datetime import datetime
from app.vturb_client import get_all_player_data
from app.core.helpers import get_date_range, get_all_players_id
from app.static_data.players_by_offer import PLAYERS_BY_OFFER

from app.models.report_model import ReportResponse
from config import TIMEZONE

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Olá, bem-vindo ao Neobright Solutions!"}


@app.get("/report/{day}")
def generate_report(day: str):
    try:
        period = get_date_range(day)
        players_id_list = get_all_players_id(players_by_offer=PLAYERS_BY_OFFER)
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
