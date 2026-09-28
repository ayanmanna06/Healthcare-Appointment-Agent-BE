from flask import Blueprint, jsonify, render_template_string

docs_bp = Blueprint("docs_bp", __name__)

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Healthcare Appointment Agent API",
        "description": "Enterprise-grade REST API for AI Agentic Healthcare Appointment Booking & Decision Engine",
        "version": "1.0.0",
        "contact": {
            "name": "Healthcare AI Support",
            "email": "support@healthagent.ai"
        }
    },
    "servers": [
        {"url": "http://localhost:5000", "description": "Local Development Server"}
    ],
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
    },
    "paths": {
        "/api/auth/register": {
            "post": {
                "summary": "Register a new user",
                "tags": ["Authentication"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["email", "password", "full_name"],
                                "properties": {
                                    "email": {"type": "string", "example": "patient@example.com"},
                                    "password": {"type": "string", "example": "secret123"},
                                    "full_name": {"type": "string", "example": "Jane Doe"},
                                    "role": {"type": "string", "enum": ["patient", "doctor", "admin"], "default": "patient"},
                                    "phone": {"type": "string", "example": "+1-555-0199"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {"description": "User successfully registered"},
                    "422": {"description": "Validation error"}
                }
            }
        },
        "/api/auth/login": {
            "post": {
                "summary": "Authenticate user and get JWT token",
                "tags": ["Authentication"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["email", "password"],
                                "properties": {
                                    "email": {"type": "string", "example": "patient@example.com"},
                                    "password": {"type": "string", "example": "secret123"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Login successful, returns JWT token"},
                    "401": {"description": "Invalid credentials"}
                }
            }
        },
        "/api/patient/symptoms": {
            "post": {
                "summary": "Core Agentic AI Workflow - Submit symptoms for full agent analysis and recommendation",
                "tags": ["AI Agents & Patient"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["symptoms"],
                                "properties": {
                                    "symptoms": {"type": "string", "example": "I have severe fever and migraine for 3 days"},
                                    "auto_book": {"type": "boolean", "default": False}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Complete agent workflow trace, diagnosis confidence, and optimal doctor recommendation"}
                }
            }
        },
        "/api/patient/recommended-doctors": {
            "get": {
                "summary": "Find recommended doctors by specialization and rating",
                "tags": ["AI Agents & Patient"],
                "parameters": [
                    {"name": "specialization", "in": "query", "schema": {"type": "string"}},
                    {"name": "min_rating", "in": "query", "schema": {"type": "number"}}
                ],
                "responses": {
                    "200": {"description": "List of matching doctors"}
                }
            }
        },
        "/api/patient/appointments/book": {
            "post": {
                "summary": "Book an appointment",
                "tags": ["Appointments"],
                "security": [{"BearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["doctor_id", "appointment_date", "start_time"],
                                "properties": {
                                    "doctor_id": {"type": "integer", "example": 1},
                                    "appointment_date": {"type": "string", "example": "2026-10-01"},
                                    "start_time": {"type": "string", "example": "09:30"},
                                    "chief_complaint": {"type": "string", "example": "Follow up consultation"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {"description": "Appointment successfully booked"}
                }
            }
        },
        "/api/admin/analytics": {
            "get": {
                "summary": "Get system-wide analytics and Chart.js datasets",
                "tags": ["Admin"],
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "Analytics data including appointment trends and specialty distribution"}
                }
            }
        }
    }
}

SWAGGER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Healthcare Appointment Agent - API Swagger Docs</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
    <style>
        body { margin: 0; padding: 0; background-color: #f8fafc; font-family: sans-serif; }
        .topbar { background: #0EA5E9; padding: 15px 30px; color: white; display: flex; align-items: center; justify-content: space-between; }
        .topbar h2 { margin: 0; font-size: 20px; }
        .swagger-ui .topbar { display: none; }
    </style>
</head>
<body>
    <div class="topbar">
        <h2>🏥 Healthcare Appointment Agent - Interactive API Docs</h2>
        <span>OpenAPI 3.0</span>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: "/api/docs/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true
            });
        };
    </script>
</body>
</html>
"""

@docs_bp.route("/openapi.json", methods=["GET"])
def get_spec():
    return jsonify(OPENAPI_SPEC)

@docs_bp.route("", methods=["GET"])
@docs_bp.route("/", methods=["GET"])
def render_swagger():
    return render_template_string(SWAGGER_HTML)
