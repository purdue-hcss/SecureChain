import pandas as pd

# Define the paths to the CSV files
conan_csv = "resources/conan/conan_all_deps.csv"
debian_csv = "resources/debian/debian_all_deps.csv"
github_csv = "resources/github/github_all_deps.csv"

# Read the CSV files and add a 'source' column to each
conan_df = pd.read_csv(conan_csv)
conan_df['source'] = 'conan'

debian_df = pd.read_csv(debian_csv)
debian_df['source'] = 'debian'

github_df = pd.read_csv(github_csv)
github_df['source'] = 'github'

# Concatenate the dataframes
combined_df = pd.concat([conan_df, debian_df, github_df], ignore_index=True)

# Drop duplicate versions, keeping the first occurrence of each version
unique_versions_df = combined_df.drop_duplicates(subset='Version')

# Sample 1000 unique versions
version_sample = unique_versions_df.sample(n=1000)

# Optional: Save the sampled versions to a new CSV file
version_sample.to_csv("resources/version_sample_with_source.csv", index=False)

# Get the list of sampled versions
sampled_versions = version_sample['Version']

# Filter the original dataframe to get all records where 'Version' is in the sampled versions
dependencies_sample = combined_df[combined_df['Version'].isin(sampled_versions)]

# Optional: Save the sampled versions and their dependencies to a new CSV file
dependencies_sample.to_csv("resources/version_dependencies_sample_with_source.csv", index=False)

# Print the first few rows of the sampled data
print(dependencies_sample.head())
