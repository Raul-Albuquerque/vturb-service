import logging
import httpx
from datetime import datetime
from typing import List
from playwright.async_api import async_playwright

from app.models.report_model import ReportResponse
from config import PLAYER_USERNAME, PLAYER_PASSWORD

BASE_URL = "https://api.vturb.com.br"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Grava no console
    ],
)


async def login_and_get_token(email, password):
    logging.info(f"Iniciando login com o email: {email}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        token = None

        async def handle_response(response):
            nonlocal token
            if "auth/login.json" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    token = data.get("token") or data.get("access_token")
                except Exception as e:
                    logging.error(f"Erro ao processar resposta de login: {e}")

        page.on("response", handle_response)

        await page.goto("https://app.vturb.com")
        await page.fill('input[name="email"]', email)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)
        await browser.close()

        if token:
            logging.info(f"Login bem-sucedido para {email}")
        else:
            logging.warning(f"Falha no login para {email}")

        return token


def get_default_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Origin": "https://app.vturb.com",
        "Referer": "https://app.vturb.com/",
    }


async def get_player_name(player_id: str, token: str):
    url = f"{BASE_URL}/vturb/v2/players/{player_id}"
    headers = get_default_headers(token)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()


async def get_player_views(player_id: str, token: str, period: dict):
    url = f"{BASE_URL}/vturb/v2/players/{player_id}/analytics_stream/player_stats"
    headers = get_default_headers(token)
    payload = {
        "player_stats": {
            "player_id": player_id,
            "start_date": period["start_date"],
            "end_date": period["end_date"],
            "timezone": "America/Sao_Paulo",
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        return response.json().get("stats", {}).get("views", {})


async def get_player_stats(player_id: str, token: str, period: dict):
    url = f"{BASE_URL}/vturb/v2/players/{player_id}/analytics_stream/player_stats_by_field"
    headers = get_default_headers(token)
    payload = {
        "player_stats_by_field": {
            "player_id": player_id,
            "start_date": period["start_date"],
            "end_date": period["end_date"],
            "timezone": "America/Sao_Paulo",
            "field": "device_type",
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        return response.json()


async def fetch_player_data(player_id: str, token: str, period: dict, max_retries=3):
    logging.info(f"Iniciando a coleta de dados para o jogador {player_id}")
    for attempt in range(1, max_retries + 1):
        try:
            pitch, stats_data, views_data = (
                await get_player_name(player_id, token),
                await get_player_stats(player_id, token, period),
                await get_player_views(player_id, token, period),
            )

            stats_list = stats_data.get("stats", [])
            total_uniq_device_events = views_data.get("totalUniqDeviceEvents", 0)

            if not pitch.get("name") or not stats_list or total_uniq_device_events == 0:
                logging.warning(
                    f"T{attempt}: dados incompletos para player {player_id}"
                )
                continue

            total_over_pitch = sum(
                item.get("total_over_pitch", 0) for item in stats_list
            )
            total_under_pitch = sum(
                item.get("total_under_pitch", 0) for item in stats_list
            )

            logging.info(f"Dados coletados com sucesso para o jogador {player_id}")
            return {
                "player_id": player_id,
                "name": pitch.get("name"),
                "totalUniqDeviceEvents": total_uniq_device_events,
                "total_over_pitch": total_over_pitch,
                "total_under_pitch": total_under_pitch,
                "error": False,
            }

        except Exception as e:
            logging.error(
                f"Erro ao processar player {player_id} (tentativa {attempt}): {e}"
            )
            continue

    logging.warning(
        f"Falha ao coletar dados para o jogador {player_id} após {max_retries} tentativas"
    )
    return {
        "player_id": player_id,
        "name": None,
        "totalUniqDeviceEvents": 0,
        "total_over_pitch": 0,
        "total_under_pitch": 0,
        "error": True,
        "message": f"Falha após {max_retries} tentativas",
    }


async def get_all_player_data(period: dict, player_ids: List[str]):
    try:
        token = await login_and_get_token(
            email=PLAYER_USERNAME, password=PLAYER_PASSWORD
        )
    except Exception as e:
        logging.error(f"Erro ao autenticar com Vturb: {e}")
        return ReportResponse(
            report_title="Get Vturb Data - Failed",
            generated_at=datetime.now(),
            count=0,
            data=[],
            status=500,
        )

    results = [await fetch_player_data(pid, token, period) for pid in player_ids]

    status_code = 200 if all(not r.get("error") for r in results) else 207

    return ReportResponse(
        report_title=(
            "Get Vturb Data - Success"
            if status_code == 200
            else "Get Vturb Data - Partial Success"
        ),
        generated_at=datetime.now(),
        count=len(results),
        data=results,
        status=status_code,
    )
