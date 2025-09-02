import pandas as pd

# Define the paths to the CSV files
file_conan_all_deps = 'resources/conan/conan_all_deps.csv'
file_debian_all_deps = 'resources/debian/debian_all_deps.csv'
file_github_all_deps = 'resources/github/github_all_deps.csv'


def merge_csv_files(files):
    # Load and concatenate the CSV files into a single DataFrame
    dfs = [pd.read_csv(file) for file in files]
    merged_df = pd.concat(dfs, ignore_index=True)
    return merged_df


def find_dependents_recursive(df, versions_to_search, level=1, visited=None, levels=None):
    """
    Recursively find dependents for a list of versions, including dependents on specific versions
    and all versions of a package (wildcard).

    :param df: DataFrame containing the dependencies
    :param versions_to_search: List of versions to search dependents for
    :param level: Current level of dependence
    :param visited: Set of visited versions to avoid cycles
    :param levels: Dictionary to store the dependence levels
    :return: Updated visited set and levels dictionary
    """
    if visited is None:
        visited = set()
    if levels is None:
        levels = {}

    for version in versions_to_search:
        if version not in visited:
            visited.add(version)

            # Find dependents for both {packageName}#{VersionNum} and {packageName}#*
            package_name = version.split('#')[0]
            specific_version_dependents = df[df['DependsOn'] == version]['Version'].tolist()
            wildcard_dependents = df[df['DependsOn'] == f"{package_name}#*"]['Version'].tolist()

            all_dependents = specific_version_dependents + wildcard_dependents

            # Mark the dependence level for these dependents
            for dependent in all_dependents:
                if dependent not in levels:
                    levels[dependent] = level

            # Recursively find dependents for these new dependents
            find_dependents_recursive(df, all_dependents, level + 1, visited, levels)

    return visited, levels


def find_all_dependents_with_levels(df, package, version):
    """
    Find all dependents with levels for a specific package version, considering both the specific version
    and all versions of the package (wildcard).

    :param df: DataFrame containing the dependencies
    :param package: The package name to search for
    :param version: The specific version to search for
    :return: DataFrame with dependents and their levels
    """
    # Start with the specific version and the wildcard version
    initial_versions_to_search = [f"{package}#{version}", f"{package}#*"]

    # Recursively find all dependents
    dependents, levels = find_dependents_recursive(df, initial_versions_to_search)

    # Convert levels dictionary to a DataFrame for better readability
    result_df = pd.DataFrame(list(levels.items()), columns=['Version', 'Dependence Level'])

    return result_df


# Merge the CSV files
merged_df = merge_csv_files([file_conan_all_deps, file_debian_all_deps, file_github_all_deps])

# Specify the package and version you're interested in
package = 'xz-utils'  # Replace with your actual package name
version = '5.6.0'  # Replace with your actual version number

# Find all dependents with levels
result_df = find_all_dependents_with_levels(merged_df, package, version)

print(f"Versions that depend on {package} and their dependence levels:")
print(result_df)

# save the result to a CSV file
result_df.to_csv('resources/dependents_with_levels.csv', index=False)