import argparse
from api import load_shares

def main():
    parser = argparse.ArgumentParser(description='Balance portfolio')
    parser.add_argument('-f', '--portfolio_file', type=str, required=True, help='JSON file containing the portfolio information')
    parser.add_argument('-a', '--amount', type=int, required=True, help='Amount to invest in the portfolio')
    parser.add_argument('-m', '--min_amount', type=int, required=False, default=0, help='Minimum amount that need to be invested per line')
    parser.add_argument('-fs', '--full_share', action='store_true', help='Only buy full share')
    #args = parser.parse_args()
    load_shares()
    return 0
if __name__ == '__main__':
    main()