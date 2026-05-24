# agents/services/openrouter.py

import logging
import time

import httpx

from django.conf import settings


logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    pass


class OpenRouterRateLimitError(
    OpenRouterError,
):
    pass


class OpenRouterClient:

    BASE_URL = (
        'https://openrouter.ai/api/v1/chat/completions'
    )

    MAX_RETRIES = 3

    RETRY_DELAY = 20

    TIMEOUT = 120

    FALLBACK_RESPONSE = (
        'I disagree with several previous '
        'arguments and believe the opposing '
        'side ignores important factors.'
    )

    def generate_response(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:

        headers = {
            'Authorization': (
                f'Bearer '
                f'{settings.OPENROUTER_API_KEY}'
            ),

            'Content-Type': 'application/json',
        }

        payload = {
            'model': model,

            'max_tokens': 1024,

            'temperature': 0.9,

            'messages': [
                {
                    'role': 'system',
                    'content': system_prompt,
                },

                *messages,
            ],
        }

        for attempt in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            try:

                response = httpx.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.TIMEOUT,
                )

                logger.info(
                    'OpenRouter status: %s',
                    response.status_code,
                )

                if response.status_code == 429:

                    logger.warning(
                        (
                            'OpenRouter rate limit. '
                            'Attempt %s/%s'
                        ),
                        attempt,
                        self.MAX_RETRIES,
                    )

                    if attempt == self.MAX_RETRIES:

                        raise (
                            OpenRouterRateLimitError(
                                'Rate limit exceeded.'
                            )
                        )

                    time.sleep(
                        self.RETRY_DELAY
                    )

                    continue

                response.raise_for_status()

                data = response.json()

                choices = data.get(
                    'choices',
                    [],
                )

                if not choices:

                    logger.warning(
                        'OpenRouter returned empty choices.'
                    )

                    return self.FALLBACK_RESPONSE

                message = choices[0].get(
                    'message',
                    {},
                )

                content = message.get(
                    'content',
                )

                if content is None:

                    logger.warning(
                        'OpenRouter returned null content.'
                    )

                    return self.FALLBACK_RESPONSE

                content = str(
                    content
                ).strip()

                if len(content) < 20:

                    logger.warning(
                        'Response too short.'
                    )

                    return self.FALLBACK_RESPONSE

                logger.info(
                    'Response generated successfully.'
                )

                return content

            except httpx.HTTPError as error:

                logger.exception(error)

                if attempt == self.MAX_RETRIES:

                    raise OpenRouterError(
                        str(error)
                    ) from error

                time.sleep(
                    self.RETRY_DELAY
                )

        return self.FALLBACK_RESPONSE