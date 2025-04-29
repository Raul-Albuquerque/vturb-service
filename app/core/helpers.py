from datetime import datetime, timedelta


def get_date_range(period: str) -> dict:
    if period == "today":
        target_date = datetime.now()
    elif period == "yesterday":
        target_date = datetime.now() - timedelta(days=1)
    else:
        raise ValueError("Período inválido. Use 'today' ou 'yesterday'.")

    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

    return {
        "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_all_players_id(players_by_offer: dict):
    players_id_list = []
    for players in players_by_offer.values():
        players_id_list.extend(players)
    return players_id_list
