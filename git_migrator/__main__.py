from .__init__ import check_data, get_data, main
from time import sleep


if __name__ == "__main__":
    check_data()
    d = get_data()
    print(f"Config: {d}")
    sleep(2)
    main()
