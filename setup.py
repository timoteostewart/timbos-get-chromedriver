from setuptools import find_packages, setup

setup(
    name="timbos_get_chromedriver",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4,<5.0",
        "lxml>=4,<5.0",
        "requests>=2.31,<3.0",
        "selenium>=4,<5.0",
        "selenium-base>=4,<5.0",
        "selenium-stealth>=1,<2.0",
        "selenium-wire>=5,<6.0",
        "undetected-chromedriver>=3.5,<4.0",
    ],
    python_requires=">=3.6",
    description="Provide a chromedriver instance",
    author="Tim Stewart",
    author_email="tim@texastim.dev",
    url="https://github.com/timoteostewart/timbos-get-chromedriver",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
