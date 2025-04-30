import logging, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from playwright.sync_api import sync_playwright

from app.models.report_model import ReportResponse

from config import PLAYER_USERNAME, PLAYER_PASSWORD

BASE_URL = "https://api.vturb.com.br"


def login_and_get_token(email, password):
    print(f"Iniciando o login para o email: {email}")
    with sync_playwright() as p:
        print("Iniciando o Playwright...")
        browser = p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        print("Navegador iniciado.")

        context = browser.new_context()
        page = context.new_page()
        print("Página criada e contexto preparado.")

        token = None
        print("Página criada e contexto preparado.")

        def handle_response(response):
            nonlocal token
            print(f"Recebendo resposta de {response.url} com status {response.status}")
            if "auth/login.json" in response.url and response.status == 200:
                try:
                    print("Resposta de login recebida, tentando extrair o token.")
                    data = response.json()
                    token = data.get("token") or data.get("access_token")
                    if token:
                        print(f"Token obtido: {token}")
                    else:
                        print("Token não encontrado na resposta.")
                except Exception as e:
                    print(f"Erro ao processar a resposta do login: {e}")

        page.on("response", handle_response)

        print("Acessando a página de login...")
        page.goto("https://app.vturb.com", timeout=15000)
        print("Página carregada.")
        page.fill('input[name="email"]', email)
        print("Email preenchido.")
        page.fill('input[name="password"]', password)
        print("Senha preenchida.")
        page.click('button[type="submit"]')
        print("Formulário de login preenchido e enviado.")

        print("Aguardando resposta...")
        page.wait_for_timeout(5000)
        print("Tempo de espera finalizado.")

        browser.close()
        print("Navegador fechado.")

        if token:
            print(f"Login bem-sucedido. Token: {token}")
        else:
            print("Falha no login. Nenhum token obtido.")

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


def get_player_name(player_id: str, token: str):
    url = f"{BASE_URL}/vturb/v2/players/{player_id}"
    headers = get_default_headers(token)

    response = requests.get(url, headers=headers)
    return response.json()


def get_player_views(player_id: str, token: str, period: dict):
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

    response = requests.post(url, headers=headers, json=payload)
    return response.json().get("stats", []).get("views")


def get_player_stats(player_id: str, token: str, period: dict):
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

    response = requests.post(url, headers=headers, json=payload)
    return response.json()


def get_all_player_data(period: dict, player_ids: List[str]) -> ReportResponse:
    try:
        token = login_and_get_token(email=PLAYER_USERNAME, password=PLAYER_PASSWORD)
    except Exception as e:
        logging.error(f"Erro ao autenticar com Vturb: {e}")
        return ReportResponse(
            report_title="Get Vturb Data - Failed",
            generated_at=datetime.now(),
            count=0,
            data=[],
            status=500,
        )

    results = []

    def fetch_player_data(player_id, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                pitch = get_player_name(player_id, token)
                stats_data = get_player_stats(player_id, token, period)
                views_data = get_player_views(player_id, token, period)

                stats_list = stats_data.get("stats", [])
                total_uniq_device_events = views_data.get("totalUniqDeviceEvents", 0)

                if (
                    not pitch.get("name")
                    or not stats_list
                    or total_uniq_device_events == 0
                ):
                    logging.warning(
                        f"Tentativa {attempt}: dados incompletos para player {player_id}"
                    )
                    continue

                total_over_pitch = sum(
                    item.get("total_over_pitch", 0) for item in stats_list
                )
                total_under_pitch = sum(
                    item.get("total_under_pitch", 0) for item in stats_list
                )

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

        return {
            "player_id": player_id,
            "name": None,
            "totalUniqDeviceEvents": 0,
            "total_over_pitch": 0,
            "total_under_pitch": 0,
            "error": True,
            "message": f"Falha após {max_retries} tentativas",
        }

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_player = {
            executor.submit(fetch_player_data, pid): pid for pid in player_ids
        }

        for future in as_completed(future_to_player):
            result = future.result()
            results.append(result)

    status_code = (
        200 if all(not r.get("error") for r in results) else 207
    )  # 207 = Multi-Status (parcial)

    return ReportResponse(
        report_title=(
            "Get Vturb Data - Partial Success"
            if status_code == 207
            else "Get Vturb Data - Success"
        ),
        generated_at=datetime.now(),
        count=len(results),
        data=results,
        status=status_code,
    )
