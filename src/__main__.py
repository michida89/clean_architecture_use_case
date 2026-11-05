from aiomisc import entrypoint

from config import config
from presenter.rest.api.router import router
from presenter.rest.app_factory import ApplicationFactory


def main() -> None:
    service = ApplicationFactory(config=config, router=router)
    with entrypoint(service) as loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
