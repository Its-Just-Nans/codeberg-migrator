from time import sleep
from .__init__ import main
from .lib import check_data, get_data


if __name__ == "__main__":
    check_data()
    d = get_data()
    print(f"Config: {d}")
    sleep(2)
    main()
