from sqlalchemy import inspect, text


def ensure_capacities_columns(engine):
    """Ensure api_credentials table has Capacities columns."""
    inspector = inspect(engine)
    if not inspector.has_table('api_credentials'):
        return
    columns = [col['name'] for col in inspector.get_columns('api_credentials')]
    statements = []
    if 'capacities_space_id' not in columns:
        statements.append(text("ALTER TABLE api_credentials ADD COLUMN capacities_space_id VARCHAR(255)"))
    if 'capacities_token' not in columns:
        statements.append(text("ALTER TABLE api_credentials ADD COLUMN capacities_token TEXT"))
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(stmt)
