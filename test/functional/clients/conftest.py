import os
import importlib.util
from os.path import join
import pytest
from .scripts import standalone


def create_cache_directories(registry, repo, digest, image_source, schema_version, cache_root):
    """
    Create a set of directories needed to save the data, skip creation if they
    are there
    """
    # The digest needs to get split because otherwise the analyzer splits on
    # ':' creating a path that is incorrect and causing failures. So this gets
    # split here, avoiding the problem
    digest = digest.split(':')[-1]
    relative_cache_path = '{image_source}/{registry}/{repo}/{digest}/{schema_version}'
    relative_cache_path = relative_cache_path.format(
        image_source=image_source,
        registry=registry,
        repo=repo,
        digest=digest,
        schema_version=schema_version
    )
    cache_path = join(cache_root, relative_cache_path)
    os.makedirs(cache_path, exist_ok=True)

    return cache_path


@pytest.fixture(scope='session')
def analyzed_data(request):
    def retrieve_cache(
        registry='docker.io', repo='centos', tag='centos8',
        digest='sha256:85313b812ad747dd19cf18078795b576cc4ae9cd2ca2ccccd7b5c12722b2effd',
        image_source='registry', schema_version='2', request=request):
        """
        The cache path gets computed by looking at the path, composed from all the arguments::

            <image_source>/<registry>/<repo>/<split digest>/<schema_version>

        For example::

            registry/docker.io/centos/85a8df7bk3j28d7f0asd8/2

        If the cache is a MISS, then the  `analyze_image()` will get called to
        produce a result module than it will get loaded and returned.

        The cache can be blown away by using ``pytest --cache-clear``. Absolute
        path to the cache directory is at the root of the project:

            {ROOT}/.pytest_cache/d/analyzer
        """
        cache_root = request.config.cache.makedir('analyzer').strpath
        cache_path = create_cache_directories(
            registry, repo, digest, image_source, schema_version,
            cache_root=cache_root)
        results_path = join(cache_path, 'result.py')
        if not os.path.exists(results_path):
            standalone.main(registry, repo, digest, tag, cache_path)

        spec = importlib.util.spec_from_file_location("functional_results", results_path)
        functional_results = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(functional_results)
        # After importing the result as a Python module, the standalone script
        # will assign the return value to `result` which is a single item in
        # a list. Return the first item in that list. If this ever fails, is
        # because the `result.py` file doesn't comply with that format
        return functional_results.result[0]

    return retrieve_cache