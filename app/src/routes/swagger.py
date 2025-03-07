from flask_swagger_ui import get_swaggerui_blueprint

SWAGGER_URL = "/apidocs"    # Ruta acceso documentacion API
API_URL = "/static/docs/main.yaml"  # Ruta main API

swagger_bp = get_swaggerui_blueprint(SWAGGER_URL, API_URL,
    config={  # Configurar OpenAPI 3.0
        "swagger": "3.0",  
        "validatorUrl": None
    })
