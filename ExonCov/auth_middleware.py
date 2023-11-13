from functools import wraps
import jwt
from flask import request, jsonify
from jwt import InvalidSignatureError

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
                "message": "Authentication Token is missing!",
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
                    "message": "Invalid Authentication token!",
                    "data": None,
                    "error": "Unauthorized"
                }), 401
        except InvalidSignatureError as ise:
            return jsonify({
                "message": "Invalid Authentication token!",
                "data": None,
                "error": "Unauthorized"
            }), 401
        except Exception as ex:
            return jsonify({
                "message": "Something went wrong",
                "data": None,
                "error": str(ex)
            }), 500

        return f(*args, **kwargs)

    return decorated
