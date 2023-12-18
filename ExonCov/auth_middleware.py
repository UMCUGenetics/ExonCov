from functools import wraps
import jwt
from flask import request, jsonify
from jwt import DecodeError

from .models import APIToken
import config


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({
                "message": "Authentication Token is missing. MH",
                "data": None,
                "error": "Unauthorized"
            }), 401
        try:
            data = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
            req_app = (
                APIToken.query
                .filter_by(token=token)
                .all()
            )
            if not req_app:
                return jsonify({
                    "message": "Invalid Authentication token. NU",
                    "data": None,
                    "error": "Unauthorized"
                }), 401
        except DecodeError as de:
            return jsonify({
                "message": "Invalid Authentication token. DE",
                "data": None,
                "error": "Unauthorized"
            }), 401
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print(message)
            return jsonify({
                "message": "Something went wrong",
                "data": None,
                "error": "See the server logs"
            }), 500

        return f(*args, **kwargs)

    return decorated
