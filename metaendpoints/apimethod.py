import json
import base64
from typing import List

from metasdk import Logger

PERMISSION_DENIED_STATUS_CODE = 7
INTERNAL_ERROR_STATUS_CODE = 13

meta_log = Logger()


class Api(object):
    """
    Функция декоратор для проверки скоупов на методах сервера

    - Проверяет наличие ОДНОГО ИЗ scopes метода в scopes токена
    - Устанавливает user_id в context сервера
    """

    def __init__(self, scopes: List[str]):
        """
        :param scopes: str[] Scope Names
        """
        self.scopes = scopes

    def __call__(self, original_func):
        decorator_self = self

        def wrappee(*args, **kwargs):
            try:
                request = args[1]
                context = args[2]

                context.user_id = None
                context.is_dev = None
                user_info = None
                imd = context.invocation_metadata()
                context.metadata = {}

                # Копируем весь imd в виде словаря, это нужно для совместимости с библиотекой grpc-testing
                for metadatum_object in imd:
                    context.metadata.update({metadatum_object.key: metadatum_object.value})

                for md in imd:
                    if md.key == 'x-endpoint-api-userinfo':
                        user_info = json.loads(base64.b64decode(md.value))

                if user_info:
                    claims = json.loads(user_info.get("claims", {}))
                    token_scopes = claims.get("scope").split(' ')  # Эти данные не нужны в самом сервисе, так как не должы определять бизнеслогику.
                    context.is_dev = 'meta.dev' in token_scopes
                    context.user_id = user_info.get("id")
                    context.metadata.update({"user_id": context.user_id, "is_dev": context.is_dev})
                    if not any((True for x in token_scopes if x in decorator_self.scopes)):
                        err_msg = 'Token expected any of scopes for this method: [' + ', '.join(decorator_self.scopes) + "]"
                        context.abort(PERMISSION_DENIED_STATUS_CODE, err_msg)
                return original_func(*args, **kwargs)
            except Exception as e:
                raise500 = False
                try:
                    if context._state and context._state.aborted:
                        err_request_ = ""

                        if request:
                            err_request_ = str(request)

                        err_code_ = str(context._state.code)
                        err_details_ = str(context._state.details.decode('utf-8'))

                        err_msg = "Abort request. Code: " + err_code_ + ". Details: " + err_details_
                        err_ctx = {
                            "request": err_request_,
                            "user": str(context.user_id)
                        }
                        if err_code_ == 'StatusCode.INTERNAL':
                            meta_log.error(err_msg, err_ctx)
                        else:
                            meta_log.warning(err_msg, err_ctx)
                    else:
                        raise500 = True
                        meta_log.error("Unhandled non context exception", {
                            "e": e
                        })
                except Exception as e:
                    raise500 = True
                    meta_log.error("Unable to log grpc abort error", {
                        "e": e
                    })
                if raise500:
                    context.abort(INTERNAL_ERROR_STATUS_CODE, "Unexpected server error")
                raise e

        return wrappee
