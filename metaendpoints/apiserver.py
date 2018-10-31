from concurrent import futures
import time
import grpc
from grpc_health.v1.health import HealthServicer
from grpc_health.v1 import health_pb2, health_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


def serve(register_servicers_callback, port: int = 50051, grace_period: int = 5):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port('[::]:{}'.format(port))

    # Регистрируем api сервисы
    register_servicers_callback(server)

    health = HealthServicer()
    health.set("plugin", health_pb2.HealthCheckResponse.ServingStatus.Value('SERVING'))
    health_pb2_grpc.add_HealthServicer_to_server(health, server)

    server.start()

    print("Server started...")

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(grace_period)
