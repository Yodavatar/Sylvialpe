<img alt="image" src="data/logo.png" style="width: 20%;"/>

# 🗺️ Sylvialpe
[![Version](https://img.shields.io/badge/version-0.0.1-blue)](https://github.com/Yodavatar/Sylvialpe)
[![License: AGPL-3.0](https://img.shields.io/badge/license-MIT-green)](https://github.com/Yodavatar/Sylvialpe/blob/main/LICENSE)


**Sylvialpe** is an automated environmental mapping and analysis tool. It makes it possible to analyze the density of urban vegetation by cutting slabs of 500m × 500m, thus providing a precise view of the green footprint of a city.

Link to the officiel website : [Sylvialpe](https://sylvialpe.yodavatar.me)
> *This project uses the open data from [Data Grand Lyon](https://data.grandlyon.com/) to power its analyses.*


### Hybrid Methodology
Sylvialpe does not use a simple pixel analysis. It relies on a robust treatment chain to distinguish real vegetation from misleading urban elements:

1. **Colorimetric Insulation:** Use of a **HSV** mask to isolate the characteristic hues of vegetation.
2. **Texture Filtering:** Application of an edge detection filter (**Canny**) to validate the roughness of the canopy.
3. **Morphological Analysis:** Closure operations to merge the trees into coherent blocks.
4. **Cleaning:** Automatic elimination of false positives (swimming pools, sports fields, shaved lawns) that have a too smooth texture.

### Density Legend

| Density | Category |
|:--- | :---- |
| **> 12%** | Forest / Dense vegetation |
| **7% to 12%** | Wooded area / Parks |
| **3% to 7%** | Mixed urban fabric |
| **< 3%** | Lean area / Concrete |

## Installation
*Note : Assurez-vous d'avoir les dépendances nécessaires (GDAL, Python 3.x, etc.) installées.*

1. **Clone the repository**:

   ```bash
   git clone git@github.com:Yodavatar/sylvialpe.git
   ```
   
2. **Get to zip**:
   You can get the link to the zip [here](https://github.com/Yodavatar/sylvialpe/archive/refs/heads/main.zip).<br>

## Usage

You need to have [python](https://www.python.org/downloads/) 3.13 or after.

## Contribution

I appreciate the others contributions from the community!<br>
To contribute to Sylvialpe, follow these steps:<br>


__**If you want contribute to this project.**__


1. Fork the repository.
2. Create a branch for your feature (`git checkout -b addmanyfeature`).
3. Commit your changes (`git commit -m 'addmanyfeature'`).
4. Push to the branch (`git push origin addmanyfeature`).
5. Open a Pull Request (`And add your message of your modifications`).

## License


This project is licensed under the MIT.<br>
See the [LICENSE](LICENSE) file for details.<br>


## Contact

If you have any questions or suggestions, <br>
feel free to contact me at contact@yodavatar.me <br>