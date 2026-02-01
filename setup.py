from setuptools import setup, find_packages

setup(
    name="fkt",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Requirements are managed in requirements.txt
    ],
    entry_points={
        'console_scripts': [
            'fkt-tracker=tracker_app.main:main',
            'fkt-dashboard=tracker_app.web.app:run_dashboard',
        ],
    },
    author="Your Name",
    description="Forgotten Knowledge Tracker - AI Spaced Repetition System",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/yourusername/FKT",
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
)
