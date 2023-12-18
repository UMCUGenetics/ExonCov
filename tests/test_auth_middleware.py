import unittest

from flask import jsonify
from jwt.exceptions import DecodeError
from unittest.mock import patch

import ExonCov.auth_middleware
from ExonCov import app
from ExonCov.auth_middleware import token_required


class MockAPIToken:
    def __init__(self, token):
        self.token = token


class FlaskAppTestCase(unittest.TestCase):

    def test_token_required(self):
        @app.route('/protected', methods=['GET'])
        @token_required
        def protected_route():
            return jsonify({"message": "Success"})

        with app.test_client() as client:
            # Test case where Authorization header is missing
            response = client.get('/protected')
            assert response.status_code == 401

            # Test case where Authorization header is present but token is missing
            response = client.get('/protected', headers={"Authorization": "Bearer "})
            assert response.status_code == 401

            # Test case where token is present but invalid
            with patch('ExonCov.auth_middleware.jwt.decode', side_effect=DecodeError()):
                response = client.get('/protected', headers={"Authorization": "Bearer invalid_token"})
                assert response.status_code == 401

            # Test case where token is valid but not found in the database
            with patch('ExonCov.auth_middleware.APIToken.query.filter_by', return_value=[]):
                response = client.get('/protected', headers={"Authorization": "Bearer valid_token"})
                assert response.status_code == 401

            # Test case where token is valid and found in the database
            with patch('flask_sqlalchemy._QueryProperty.__get__') as queryMOCK:
                queryMOCK \
                    .return_value.filter_by \
                    .return_value.all \
                    .return_value = [MockAPIToken("valid_token")]

                # get actual
                req_app = ExonCov.models.APIToken.query.filter_by().all()
                with patch('ExonCov.auth_middleware.jwt.decode', return_value={"data": "decoded_data"}):
                    response = client.get('/protected', headers={"Authorization": "Bearer valid_token"})
                    assert response.status_code == 200
                    assert response.json == {"message": "Success"}
