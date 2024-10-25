import json
import logging
from typing import Any, Dict

import requests
from .openapi_spec import OpenAPISpec, OpenAPISpecError

from swarm.types import Agent, AgentFunction, Result

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Changed from DEBUG to INFO


class OpenAPIAgent(Agent):
    class Config:
        extra = 'allow'  # This allows setting extra fields dynamically.

    def route_request(self, method: str, path: str) -> Result:
        logger.info(f"Routing request to: {method} {path}")
        return Result(
            value=f"Transferring to API Caller Agent: {method} {path}",
            agent=self.api_caller_agent,
            context_variables={"path": path, "method": method}
        )

    def __init__(self, spec_path: str, auth_class=None, name="OpenAPI Agent"):
        super().__init__(name=name, model='gpt-4o-mini')
        self.auth = auth_class() if auth_class else None
        self.openapi_spec = self._load_openapi_spec(spec_path)
        self.api_caller_agent = self._create_api_caller_agent()
        self.instructions = self._get_instructions()
        self.functions = [self.route_request]
        logger.info(f"Initialized {name} with spec from {spec_path}")

    def _load_openapi_spec(self, spec_path: str) -> OpenAPISpec:
        try:
            spec = OpenAPISpec(spec_path)
            logger.info(
                f"Successfully loaded OpenAPI specification from {spec_path}")
            return spec
        except OpenAPISpecError as e:
            logger.error(f"Failed to load OpenAPI specification from {
                         spec_path}: {str(e)}")
            raise

    def _get_instructions(self, ) -> str:
        paths = self.openapi_spec.get_all_paths()
        paths_summary = "\n".join(
            [f"{method} {path}: {summary}" for method, path, summary in paths])

        instructions = f"""
        You are a router agent for an OpenAPI-based service. Your task is to find the most appropriate API path and method based on the user's request.
        Here are all the available paths and their summaries:

        {paths_summary}

        When a user request comes in, analyze it and determine the most appropriate method and path.
        Then call the route_request function with the chosen method and path.
        """
        return instructions

    def get_auth_token(self):
        if self.auth:
            logger.debug("Attempting to get auth token")
            token = self.auth.authenticate()['access_token']
            logger.info("Successfully obtained auth token")
            return token
        logger.debug("No auth class provided, skipping authentication")
        return None

    def call_api(self, endpoint: str, params: Dict[str, Any] = None, method: str = 'GET', data: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.info(f"Initiating API call: {method} {endpoint}")
        token = self.get_auth_token()
        base_url = self.openapi_spec.spec.get('servers', [{}])[0].get('url', '')
        # Remove leading '/' from endpoint if present
        endpoint = endpoint.lstrip('/')
        url = f"{base_url}/{endpoint}"

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.debug(f"Making request to {url} with params: {params} and data: {data}")
        response = requests.request(method, url, headers=headers, params=params, json=data)

        if response.status_code == 401 and self.auth:
            logger.warning("Received 401 Unauthorized, attempting to refresh token")
            token = self.get_auth_token()  # This will refresh the token if needed
            headers["Authorization"] = f"Bearer {token}"
            logger.info("Retrying request with new token")
            response = requests.request(method, url, headers=headers, params=params, json=data)

        if response.ok:
            logger.info(f"API call successful: {method} {endpoint} (Status: {response.status_code})")
            return response.json() if response.text else None
        else:
            error_message = f"API call failed: {method} {endpoint} (Status: {response.status_code})"
            logger.error(error_message)
            logger.error(f"Error details: {response.text}")
            return {"error": error_message, "details": response.text}

    def _create_api_caller_agent(self) -> Agent:
        def generate_instructions(context_variables: Dict[str, Any]) -> str:
            method = context_variables.get('method', '')
            path = context_variables.get('path', '')
            api_details = self.openapi_spec.get_api_details(path, method)

            if not api_details:
                return f"No API details found for {method.upper()} {path}"

            instructions = f"""
            You are an API Caller Agent responsible for generating appropriate parameters for the following API call:

            \n\n\n
            {method.upper()} {path}
            \n
            {json.dumps(api_details, indent=2)}
            """

            instructions += """
            Your task is to analyze the user's request and generate the necessary parameters for this API call.
            Make sure to adhere to the parameter requirements, types, and constraints specified above.
            """

            return instructions

        return Agent(
            name="API Caller Agent",
            model='gpt-4o-mini',
            instructions=generate_instructions,
            functions=[self.call_api]
        )
