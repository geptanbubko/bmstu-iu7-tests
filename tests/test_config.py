from pathlib import Path

from wildlife_app.config import load_config


def test_load_config_reads_db_and_business_param(tmp_path: Path) -> None:
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        """
[database]
connection_string = sqlite:///data/app.db

[business]
min_records_for_trend = 7

[logging]
level = DEBUG
file = logs/test.log
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.database_path == tmp_path / "data" / "app.db"
    assert config.min_records_for_trend == 7
    assert config.log_level == "DEBUG"
    assert config.log_file == tmp_path / "logs" / "test.log"
    assert config.gui_host == "127.0.0.1"
    assert config.gui_port == 5000
