"""Демонстрационный сценарий MVP через HTTP API развёрнутого стенда.

Администратор заводит вид, локацию и исследователя → исследователь фиксирует
пять ежемесячных наблюдений → видит их в журнале → получает анализ с трендом.
Повторяет сценарии 1–3 из README (раздел 9) без GUI.
"""
import allure

pytestmark = [
    allure.epic("Мониторинг популяции диких животных"),
    allure.feature("E2E: демонстрационный сценарий"),
]

SURVEY = (("2025-04-10", 3), ("2025-05-10", 5), ("2025-06-10", 6), ("2025-07-10", 8), ("2025-08-10", 9))


@allure.story("Сквозной сценарий учёта популяции")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("Администратор заполняет справочники, исследователь фиксирует учёт и получает тренд")
def test_population_monitoring_scenario(api, run_tag) -> None:
    # arrange: уникальные данные прогона и две роли
    species_body = {"scientific_name": f"Vulpes lagopus e2e-{run_tag}", "common_name": "Песец"}
    location_body = {"name": f"Хибины e2e-{run_tag}", "region": "Мурманская область"}
    researcher_body = {"full_name": f"Тестов Т.Т. e2e-{run_tag}", "organization": "ИУ7"}
    admin = api.login("admin")
    researcher = api.login("researcher")

    with allure.step("act: администратор заполняет справочники"):
        species = api.call("POST", "/species", species_body, token=admin)
        location = api.call("POST", "/locations", location_body, token=admin)
        person = api.call("POST", "/researchers", researcher_body, token=admin)
        duplicate = api.call("POST", "/species", species_body, token=admin)

    with allure.step("assert: справочники сохранены, дубликат вида отклонён"):
        assert (species.status, location.status, person.status) == (201, 201, 201)
        assert species.body["common_name"] == "Песец"
        assert duplicate.status == 409

    refs = {
        "species_id": species.body["id"],
        "location_id": location.body["id"],
        "researcher_id": person.body["id"],
    }
    with allure.step("act: исследователь фиксирует пять ежемесячных наблюдений"):
        created = [
            api.call(
                "POST",
                "/observations",
                {**refs, "observation_date": day, "individuals_count": count, "notes": run_tag},
                token=researcher,
            )
            for day, count in SURVEY
        ]
        forbidden = api.call("POST", "/observations", {**refs, "observation_date": "2025-09-10",
                                                      "individuals_count": 1}, token=admin)

    with allure.step("assert: наблюдения приняты, у администратора нет прав на запись наблюдений"):
        assert [r.status for r in created] == [201] * len(SURVEY)
        assert forbidden.status == 403

    with allure.step("act: исследователь открывает журнал и анализ динамики за 2025 год"):
        journal = api.call("GET", "/observations", token=researcher)
        query = (
            f"/analytics/population?species_id={refs['species_id']}"
            f"&date_from=2025-01-01&date_to=2025-12-31&location_id={refs['location_id']}"
        )
        analysis = api.call("GET", query, token=researcher)

    with allure.step("assert: журнал содержит наблюдения прогона, тренд построен"):
        mine = [o for o in journal.body if o["notes"] == run_tag]
        assert journal.status == 200
        assert [(o["observation_date"], o["individuals_count"]) for o in mine] == list(SURVEY)
        assert analysis.status == 200
        assert analysis.body["records_count"] == len(SURVEY)
        assert analysis.body["has_trend"] is True
        assert analysis.body["rows"][-1] == {"date": "2025-08-10", "population_size": 9}
