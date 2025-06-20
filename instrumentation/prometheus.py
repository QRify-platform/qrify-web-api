from prometheus_fastapi_instrumentator import Instrumentator

def instrument_app(app):
    Instrumentator().instrument(app).expose(app)
