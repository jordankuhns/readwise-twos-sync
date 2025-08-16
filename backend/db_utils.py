from sqlalchemy import inspect, text


def ensure_capacities_columns(engine):
    """Ensure api_credentials table has Capacities columns."""
    inspector = inspect(engine)
    if not inspector.has_table('api_credentials'):
        return
    columns_info = inspector.get_columns('api_credentials')
    columns = {col['name']: col for col in columns_info}
    statements = []
    if 'capacities_space_id' not in columns:
        statements.append(text("ALTER TABLE api_credentials ADD COLUMN capacities_space_id VARCHAR(255)"))
    if 'capacities_token' not in columns:
        statements.append(text("ALTER TABLE api_credentials ADD COLUMN capacities_token TEXT"))
    # Ensure Twos columns are nullable
    twos_user_col = columns.get('twos_user_id')
    if twos_user_col and not twos_user_col.get('nullable', True):
        statements.append(text("ALTER TABLE api_credentials ALTER COLUMN twos_user_id DROP NOT NULL"))
    twos_token_col = columns.get('twos_token')
    if twos_token_col and not twos_token_col.get('nullable', True):
        statements.append(text("ALTER TABLE api_credentials ALTER COLUMN twos_token DROP NOT NULL"))
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(stmt)
