# Spatial K-Fold Cross-Validation for Surface Generalization

## Overview
Spatial K-Fold Cross-Validation is a validation strategy specifically designed for geospatial data. Unlike standard K-Fold cross-validation, which splits data randomly, Spatial K-Fold ensures that the training and test sets are spatially disjoint. This is typically achieved by dividing the spatial domain into varying blocks or clusters and ensuring that all data points within a specific block belong exclusively to either the training or the test set.

## Why is it Useful?

### Addressing Spatial Autocorrelation
The primary motivation for Spatial K-Fold is **Spatial Autocorrelation**: the principle that points close to each other in space are more likely to have similar values (Tobler's First Law of Geography). 

In standard random K-Fold:
- A test point is geographically surrounded by training points.
- The model can simply "memorize" the local neighborhood rather than learning the underlying spatial structure or trend.
- This leads to an **optimistically biased performance estimate**, suggesting the model generalizes better than it actually does.

In Spatial K-Fold:
- The model is tested on a distinct region (a "hole" in the map) derived from the held-out block.
- To succeed, the model must effectively interpolate or extrapolate trends across distance.
- This provides a much more realistic metric of how the surface will behave in areas where no sensors exist.

### Promoting Robust Interpolation
For Radial Basis Function (RBF) networks and other interpolation methods, the goal is often to generate a smooth surface that intuitively fills gaps. Spatial K-Fold forces the hyperparameter search (e.g., finding the optimal `epsilon`) to prioritize parameters that create stable, generalizing surfaces rather than parameters that create minute, high-frequency spikes to fit immediate neighbors.

## Assumptions

When applying Spatial K-Fold (and subsequently using the validated model), we rely on several key assumptions:

1.  **Stationarity:**
    We assume that the statistical properties (mean, variance, spatial structure) of the data are relatively constant across the domain. If the northern part of the region follows a completely different physical regime than the southern part, a model trained on the south cannot accurately predict the north, regardless of the validation scheme. Use of Spatial K-Fold implies we believe the "rules" of the surface are universal enough to be learned in one area and applied to another.

2.  **Spatial Continuity:**
    We assume the underlying phenomenon is continuous. If the data contains sharp, physical discontinuities (like a cliff face or a discrete boundary of a smoke plume), RBF and averaging methods validated this way may over-smooth these boundaries unless specifically accounted for.

3.  **Representative Sampling:**
    We assume that the spatial blocks chosen for training are representative of the overall domain. If all high-value clusters are accidentally segregated into a single fold, the model may fail to learn the full range of the variable. (Stratified variants of Spatial K-Fold can help here).

4.  **Isotropy (Context Dependent):**
    Many standard RBF kernels (like Gaussian) assume isotropy—that the spatial correlation decays at the same rate in all directions. While Spatial K-Fold doesn't strict *require* this, using it to select a single scalar `epsilon` implies we are searching for a globally valid smoothing parameter that works in all directions.
