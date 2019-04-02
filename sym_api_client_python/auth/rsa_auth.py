import json
import requests
import datetime
import time
import logging

from jose import jwt
from ..clients.api_client import APIClient


class SymBotRSAAuth(APIClient):
    """Class for RSA authentication"""

    def __init__(self, config):
        """
        Set up proxy information if configuration contains proxyURL

        :param config: Object contains all RSA configurations
        """
        self.config = config
        self.last_auth_time = 0
        self.session_token = None
        self.key_manager_token = None
        self.auth_session = requests.Session()
        if (self.config.data['truststorePath']):
            logging.debug("Setting trusstorePath for auth to {}".format(self.config.data['truststorePath']))
            self.auth_session.verify=self.config.data['truststorePath']
        if self.config.data['completeProxyURL']:
            self.auth_session.proxies.update({
                "http": self.config.data['completeProxyURL'],
                "https": self.config.data['completeProxyURL']})
        else:
            self.proxies = {}

    def get_session_token(self):
        """Return the session token"""
        return self.session_token

    def get_key_manager_token(self):
        """Return the key manager token"""
        return self.key_manager_token

    def authenticate(self):
        """
        Get the session and key manager token
        """
        logging.debug('Auth/authenticate()')
        if (self.last_auth_time == 0) or (int(round(time.time() * 1000) -
                                              self.last_auth_time >= 3000)):
            logging.debug('Auth/authenticate() --> needed to authenticate')
            self.last_auth_time = int(round(time.time() * 1000))
            self.session_authenticate()
            self.key_manager_authenticate()
        else:
            try:
                logging.debug('Retry authentication in 30 seconds.')
                time.sleep(30)
                self.authenticate()
            except Exception as err:
                print(err)

    def create_jwt(self):
        """
        Create a jwt token with payload dictionary. Encode with
        RSA private key using RS512 algorithm

        :return: A jwt token valid for < 290 seconds
        """
        logging.debug('RSA_auth/getJWT() function started')
        with open(self.config.data['botRSAPath'], 'r') as f:
            content = f.readlines()
            private_key = ''.join(content)
            expiration_date = int(datetime.datetime.now(datetime.timezone.utc)
                                  .timestamp() + (5*58))
            payload = {
                'sub': self.config.data['botUsername'],
                'exp': expiration_date
            }
            encoded = jwt.encode(payload, private_key, algorithm='RS512')
            f.close()
            return encoded

    def session_authenticate(self):
        """
        Get the session token by calling API using jwt token
        """
        logging.debug('RSA_auth/get_session_token() function started')
        data = {
            'token': self.create_jwt()
        }
        url = self.config.data['sessionAuthHost']+'/login/pubkey/authenticate'
        response = self.auth_session.post(url, json=data)
        if response.status_code == 200:
            data = json.loads(response.text)
            self.session_token = data['token']
        else:
            logging.debug('RSA_auth/get_session_token() function failed')
            self.authenticate()

    def key_manager_authenticate(self):
        """
        Get the key manager token by calling API using jwt token
        """
        logging.debug('RSA_auth/get_keyauth() function started')
        data = {
            'token': self.create_jwt()
        }
        url = self.config.data['keyAuthHost']+'/relay/pubkey/authenticate'
        response = self.auth_session.post(url, json=data)
        if response.status_code == 200:
            data = json.loads(response.text)
            self.key_manager_token = data['token']
        else:
            logging.debug('RSA_auth/get_keyauth() function failed')
            self.authenticate()
