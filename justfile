# [windows]
set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

modules:
    mpremote mip install logging github:mcauser/micropython-tm1637 github:josverl/micropython-stubs/mip/typing_mpy.json

[working-directory: "./src"]
deploy:
    mpremote cp -r . :
    # mpremote rm -rf :__pycache__
