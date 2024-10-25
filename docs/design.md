# Design Document for Spotify Agent

## Agent Architecture

The agent is designed with a 2-layer architecture:

1. **Router Agent**: Responsible for routing the user's request to the appropriate agent.
2. **Web Call Agent**: Responsible for solving the user's request by making the necessary web calls.

### OpenAPI Specification Parser

The OpenAPI Specification parser is tasked with parsing the OpenAPI Specification to extract necessary information for solving user requests.

- **Input**: The OpenAPI Specification
- **Output**: API paths and corresponding summaries

*Note*: The specification may use `$ref` to reference parameter schemas. These references need to be resolved to obtain the full API path.

### Router Agent

The router agent routes the user's request to the appropriate agent using a combination of rule-based matching and a Language Learning Model (LLM).

- **Responsibilities**:
  - Find the API path for the user's request.
  - Utilize the API paths and corresponding summaries: `${api_paths}`

- **Tools**:
  - `transfer_to_web_call_agent`: Transfers the user's request and the API path to the web call agent.

### Web Call Agent

Once the router agent identifies the web path, it transfers the user's request and the web path to the web call agent. The web call agent extracts the corresponding web call and parameter descriptions from the OpenAPI Specification, submits them to the LLM to generate the final request, and then calls the web path.

- **Responsibilities**:
  - Extract the web call and parameter descriptions from the OpenAPI Specification.
  - Submit the web call and parameters to the LLM to generate the final request.
  - Call the web path with the final request.

- **Tools**:
  - `call_web_path`: Executes the web path with the final request.
  - `transfer_to_router_agent`: Transfers the user's request and the web path back to the router agent if needed.

## Agent Interaction

The router agent and the web call agent interact through the `transfer_to_web_call_agent` and `transfer_to_router_agent` tools.
