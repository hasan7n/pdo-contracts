SCRIPTDIR="$(dirname $(readlink --canonicalize ${BASH_SOURCE}))"
SOURCE_ROOT="$(realpath ${SCRIPTDIR}/..)"
rm -f ${SOURCE_ROOT}/test/*_db ${SOURCE_ROOT}/test/*-lock ${SOURCE_ROOT}/test/test_context.toml