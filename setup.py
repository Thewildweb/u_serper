from distutils.core import setup

setup(
    name="u_serper",
    version="0.01",
    description="Client to get emails for domains with Snovio",
    author="Erik Meijer",
    author_email="erik@datadepartment.io",
    url="https://www.datadepartment.io",
    packages=["u_serper"],
    install_requires=["aiohttp", "pydantic", "tenacity"],
)
