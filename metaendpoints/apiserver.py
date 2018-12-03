from concurrent import futures
import time
import grpc
from grpc_health.v1.health import HealthServicer
from grpc_health.v1 import health_pb2, health_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


def serve(register_servicers_callbacks=None, port: int = 50051, grace_period: int = 10):
    """
    Старт GRPC сервера

    :param register_servicers_callbacks: Список колбеков для регистрации сервисов апи в grpc сервере
    :param port: grpc порт. Менять не желательно
    :param grace_period: Период ожидания завершения подключений (https://grpc.io/grpc/python/grpc.html#grpc.Server.stop)
    :return:
    """
    if register_servicers_callbacks is None:
        register_servicers_callbacks = []

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port('[::]:{}'.format(port))

    # Регистрируем api сервисы
    for callback_ in register_servicers_callbacks:
        callback_(server)

    health = HealthServicer()
    health.set("health", health_pb2.HealthCheckResponse.ServingStatus.Value('SERVING'))
    health_pb2_grpc.add_HealthServicer_to_server(health, server)

    server.start()

    print("Server started...")

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(grace_period)
