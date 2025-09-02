import pandas as pd

file_699 = 'resources/cwe/699.csv'
file_1000 = 'resources/cwe/1000.csv'
file_1194 = 'resources/cwe/1194.csv'
file_cwe = 'resources/cwe/all_cwe.csv'


def load_all_cwes():
    cwe_699 = pd.read_csv(file_699)
    cwe_1000 = pd.read_csv(file_1000)
    cwe_1194 = pd.read_csv(file_1194)
    # merge the dataframes, but keep the original index
    cwe = pd.concat([cwe_699, cwe_1000, cwe_1194], ignore_index=True)
    print(cwe)
    return cwe


def save_all_cwes():
    cwe = load_all_cwes()
    # save the cwe to a csv file
    cwe.to_csv(file_cwe)
    print(cwe)


def main():
    save_all_cwes()


if __name__ == '__main__':
    main()
