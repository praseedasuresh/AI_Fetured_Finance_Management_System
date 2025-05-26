# SentiMeld: Advanced Sentiment Analysis Platform

An innovative sentiment analysis tool that combines multiple NLP approaches to provide comprehensive sentiment insights from text data.

## Features

- **Ensemble Approach**: Combines traditional ML (NLTK), deep learning (Transformers), and rule-based methods for robust sentiment analysis
- **Multi-dimensional Analysis**: Goes beyond positive/negative classification to detect emotions, intensity, and aspect-based sentiments
- **Interactive Visualization**: Explore sentiment patterns with dynamic dashboards
- **Customizable Pipeline**: Easily adapt to different domains (tweets, product reviews, etc.)
- **Explainable Results**: Understand what drives sentiment scores with feature importance and attention visualization
- **API Integration**: Seamlessly integrate with other applications

## Project Structure

```
SentiMeld/
├── data/                  # Data storage and processing
│   ├── raw/               # Raw datasets
│   ├── processed/         # Processed datasets
│   └── data_loader.py     # Data loading utilities
├── models/                # Model implementations
│   ├── traditional.py     # NLTK and traditional ML models
│   ├── deep_learning.py   # Transformer-based models
│   ├── ensemble.py        # Ensemble model implementation
│   └── aspect_based.py    # Aspect-based sentiment analysis
├── preprocessing/         # Text preprocessing pipeline
│   ├── cleaner.py         # Text cleaning utilities
│   ├── tokenizer.py       # Tokenization utilities
│   └── feature_extractor.py # Feature extraction utilities
├── training/              # Model training scripts
│   ├── train.py           # Main training script
│   └── evaluate.py        # Evaluation utilities
├── visualization/         # Visualization tools
│   ├── dashboard.py       # Interactive dashboard
│   └── plots.py           # Static visualization utilities
├── api/                   # API implementation
│   ├── app.py             # Flask API
│   └── endpoints.py       # API endpoints
├── utils/                 # Utility functions
│   ├── metrics.py         # Custom metrics
│   └── helpers.py         # Helper functions
├── main.py                # Main entry point
├── config.py              # Configuration
├── requirements.txt       # Dependencies
└── README.md              # Documentation
```

## Getting Started

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Download required NLTK data:
   ```
   python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
   ```
4. Download SpaCy model:
   ```
   python -m spacy download en_core_web_sm
   ```

### Usage

#### Training Models

```python
python main.py --mode train --data path/to/data --model ensemble
```

#### Analyzing Text

```python
python main.py --mode analyze --text "This product is amazing! Highly recommended."
```

#### Running the Dashboard

```python
python visualization/dashboard.py
```

## What Makes SentiMeld Different?

1. **Ensemble Architecture**: Unlike most sentiment tools that rely on a single approach, SentiMeld combines multiple methods for more accurate results.
2. **Contextual Understanding**: Uses transformer models to capture context and nuance in language.
3. **Aspect-Based Analysis**: Identifies specific aspects being discussed and their associated sentiments.
4. **Emotion Detection**: Goes beyond positive/negative to detect specific emotions (joy, anger, surprise, etc.).
5. **Interactive Exploration**: Provides tools to explore and understand sentiment patterns in your data.
6. **Customizable Pipeline**: Easily adapt to different domains with transfer learning.


## Project Structure

The project is now properly organized with:

- A dedicated dataset directory containing the IMDB Dataset
- Proper path handling in all modules
- Consistent directory structure
The SentiMeld project combines multiple approaches to sentiment analysis, including traditional machine learning models, transformer-based models, and ensemble methods, providing a comprehensive solution for sentiment analysis tasks.





## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
