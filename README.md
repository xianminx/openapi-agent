# OpenAPI Agent

OpenAPI Agent is a simple yet powerful Python package that makes working with OpenAPI-based services easier. It uses AI to understand what you want to do and connects to the right API endpoints for you. The agent works with OpenAI's [Swarm](https://github.com/openai/swarm) library to talk to the OpenAI API.

Here's what OpenAPI Agent does:

1. Understands your requests
2. Finds the right API endpoint
3. Makes API calls for you

Whether you're new to APIs or an experienced developer, OpenAPI Agent can help you interact with services more easily and efficiently.

## Installation

You can install the OpenAPI Agent using pip:

```bash
pip install git+https://github.com/xianminx/openapi-agent.git
```

For development installation:

```bash
git clone https://github.com/xianminx/openapi-agent.git
cd openapi-agent
pip install .
```

## Usage

Here's a basic example of how to use the OpenAPI Agent:

```python
from swarm.repl import run_demo_loop
from openapi_agent import OpenAPIAgent

# Initialize the agent with an OpenAPI specification
agent = OpenAPIAgent("path/to/openapi_spec.json")

print("Welcome to the OpenAPI Agent! Tell me what you want to do.")
run_demo_loop(agent)
```

### Configuration

The OpenAPIAgent class accepts the following parameters:

- `spec_path`: Path to the OpenAPI specification file (required)
- `model`: The AI model to use (default: 'gpt-4o-mini')
- `auth_class`: A class to handle authentication (optional)
- `name`: Name of the agent (default: "OpenAPI Agent")

## Running Tests

To run the tests, use the following command:

```bash
pytest
```

## Contributing

We welcome contributions from the open-source community! To get started, follow these steps to set up the project using Poetry:

1. Ensure you have Poetry installed. If not, install it by following the instructions at [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation).

2. Clone the repository:

   ```sh
   git clone https://github.com/xianminx/openapi-agent.git
   cd openapi-agent
   ```

3. (Optional) Configure Poetry to create the virtual environment in the project directory:

   ```sh
   poetry config virtualenvs.in-project true
   ```

   This step is optional but recommended for better project isolation.

4. Install the project dependencies:

   ```sh
   poetry install
   ```

5. Activate the virtual environment:

   ```sh
   poetry shell
   ```

6. Run tests to ensure everything is set up correctly:

   ```sh
   pytest
   ```

7. Make your changes and create a pull request with a clear description of the modifications.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the Swarm library
- The OpenAPI Initiative for the OpenAPI Specification

## Contact

If you have any questions, feel free to open an issue or contact the maintainers directly.
