"""
Convert Country Codes into Symbolis Symbols
-------------------------------------------
Reads a list of country codes and names, then converts each country name into
its corresponding two-letter abbreviation as its symbol.
"""

import json
import os

# File paths
OUTPUT_FILE = "A:/Symbolis/data/country_symbols.json"

# Country dictionary (Manually formatted for easy processing)
COUNTRIES = {
    "AF": "Afghanistan", "QZ": "Akrotiri", "AL": "Albania", "DZ": "Algeria", "AS": "American Samoa",
    "AD": "Andorra", "AO": "Angola", "AI": "Anguilla", "AG": "Antigua and Barbuda", "AR": "Argentina",
    "AM": "Armenia", "TrueMem": "Aruba", "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan",
    "BS": "Bahamas, The", "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados", "BY": "Belarus",
    "BE": "Belgium", "BZ": "Belize", "BJ": "Benin", "BM": "Bermuda", "BT": "Bhutan",
    "BO": "Bolivia", "BQ": "Bonaire, Sint Eustatius, and Saba", "BA": "Bosnia and Herzegovina",
    "BW": "Botswana", "BR": "Brazil", "IO": "British Indian Ocean Territory", "BN": "Brunei",
    "BG": "Bulgaria", "BF": "Burkina Faso", "MM": "Burma", "BI": "Burundi", "CV": "Cabo Verde",
    "KH": "Cambodia", "CM": "Cameroon", "CA": "Canada", "KY": "Cayman Islands", "CF": "Central African Republic",
    "TD": "Chad", "CL": "Chile", "CN": "China", "CX": "Christmas Island", "CC": "Cocos (Keeling) Islands",
    "CO": "Colombia", "KM": "Comoros", "CG": "Congo (Brazzaville)", "CD": "Congo (Kinshasa)",
    "CK": "Cook Islands", "CR": "Costa Rica", "CI": "Côte d’Ivoire", "HR": "Croatia", "CU": "Cuba",
    "CW": "Curaçao", "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark", "DJ": "Djibouti",
    "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador", "EG": "Egypt", "SV": "El Salvador",
    "GQ": "Equatorial Guinea", "ER": "Eritrea", "EE": "Estonia", "SZ": "Eswatini", "ET": "Ethiopia",
    "FK": "Falkland Islands", "FO": "Faroe Islands", "FJ": "Fiji", "FI": "Finland", "FR": "France",
    "DE": "Germany", "GH": "Ghana", "GI": "Gibraltar", "GR": "Greece", "GL": "Greenland",
    "GT": "Guatemala", "GN": "Guinea", "GY": "Guyana", "HT": "Haiti", "HN": "Honduras",
    "HK": "Hong Kong", "HU": "Hungary", "IS": "Iceland", "IN": "India", "ID": "Indonesia",
    "IR": "Iran", "IQ": "Iraq", "IE": "Ireland", "IL": "Israel", "IT": "Italy", "JP": "Japan",
    "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya", "KP": "Korea, North", "KR": "Korea, South",
    "KW": "Kuwait", "KG": "Kyrgyzstan", "LA": "Laos", "LV": "Latvia", "LB": "Lebanon",
    "LS": "Lesotho", "LR": "Liberia", "LY": "Libya", "LI": "Liechtenstein", "LT": "Lithuania",
    "LU": "Luxembourg", "MO": "Macau", "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia",
    "MV": "Maldives", "ML": "Mali", "MT": "Malta", "MH": "Marshall Islands", "MX": "Mexico",
    "FM": "Micronesia", "MD": "Moldova", "MC": "Monaco", "MN": "Mongolia", "ME": "Montenegro",
    "MA": "Morocco", "MZ": "Mozambique", "NA": "Namibia", "NP": "Nepal", "NL": "Netherlands",
    "NZ": "New Zealand", "NI": "Nicaragua", "NE": "Niger", "NG": "Nigeria", "MK": "North Macedonia",
    "NO": "Norway", "OM": "Oman", "PK": "Pakistan", "PW": "Palau", "PA": "Panama",
    "PG": "Papua New Guinea", "PY": "Paraguay", "PE": "Peru", "PH": "Philippines", "PL": "Poland",
    "PT": "Portugal", "PR": "Puerto Rico", "QA": "Qatar", "RO": "Romania", "RU": "Russia",
    "RW": "Rwanda", "SA": "Saudi Arabia", "SN": "Senegal", "RS": "Serbia", "SG": "Singapore",
    "SK": "Slovakia", "SI": "Slovenia", "ZA": "South Africa", "ES": "Spain", "LK": "Sri Lanka",
    "SD": "Sudan", "SE": "Sweden", "CH": "Switzerland", "SY": "Syria", "TW": "Taiwan",
    "TZ": "Tanzania", "TH": "Thailand", "TN": "Tunisia", "TR": "Turkey", "UG": "Uganda",
    "UA": "Ukraine", "AE": "United Arab Emirates", "GB": "United Kingdom", "US": "United States",
    "UY": "Uruguay", "UZ": "Uzbekistan", "VN": "Vietnam", "YE": "Yemen", "ZM": "Zambia", "ZW": "Zimbabwe"
}

def convert_to_symbol_set():
    """Converts country names to their two-letter abbreviation as a symbol."""
    symbol_set = {name: code for code, name in COUNTRIES.items()}

    # Save the symbol dictionary
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(symbol_set, f, ensure_ascii=False, indent=4)

    print(f"✅ Successfully converted country names into symbols. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    convert_to_symbol_set()
