# Sexual-Dimorphism-in-Flies-Wing-Cells

Geometric Morphometrics Pipeline for Fly Wing AnalysisThis repository contains a complete bioinformatics pipeline for analyzing wing shape variations in Diptera species (e.g., Calliphora vicina, Chrysomya albiceps) using Elliptic Fourier Descriptors (EFD).The project investigates Sexual Dimorphism and Geographic Variation (Locality) by processing wing images, generating shape coefficients, performing statistical tests (PCA, MANOVA, Hotelling's T2), and creating interactive 3D visualizations.

Repository Structure

1. Data Processing
efd_generation.r: The starting point. Reads raw wing images, normalizes them (size, rotation, phase) using Momocs, and generates Elliptic Fourier Descriptors. Uses parallel processing to handle large datasets.

PCA_1.r: Performs Principal Component Analysis (PCA) on the normalized EFD coefficients. It automatically selects the number of Principal Components (PCs) required to explain 90% of the variance.

2. Statistical Analysis
manova.r: Runs Multivariate Analysis of Variance (MANOVA) to calculate the percentage of shape variation attributed to Species, Sex, Locality, and their interactions.

hottelling.r: Performs Hotelling’s T2 test to determine if the shape difference between Males and Females is statistically significant within specific populations (Species + Locality).

3. Visualization
contour_check.py: Reconstructs the average wing shapes from EFD coefficients. Plots Mean Male vs. Mean Female outlines to visually verify shape differences.

plot_PCA_1.py: Generates high-quality, interactive 3D Scatter Plots using Plotly. Features custom styling (Lato font), grouping by population, and detailed hover information.

R Dependencies
install.packages(c("Momocs", "imager", "tidyverse", "foreach", "doParallel", "MASS", "ggplot2", "scales"))

Python Dependencies
pip install pandas numpy matplotlib plotly
