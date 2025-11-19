"""
Data Quality Checker
Validates and cleans market data for trading strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from src.utils.logger import TradingLogger

logger = TradingLogger("DataQuality")


class DataQualityChecker:
    """
    Data Quality and Validation
    Ensures market data is clean and reliable for trading
    """

    @staticmethod
    def validate_ohlc(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate OHLC data consistency

        Args:
            df: DataFrame with OHLC columns

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        required_columns = ['open', 'high', 'low', 'close']

        # Check for required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
            return False, errors

        # Check High >= Low
        invalid_hl = df[df['high'] < df['low']]
        if len(invalid_hl) > 0:
            errors.append(f"Found {len(invalid_hl)} rows where High < Low")

        # Check High >= Open
        invalid_ho = df[df['high'] < df['open']]
        if len(invalid_ho) > 0:
            errors.append(f"Found {len(invalid_ho)} rows where High < Open")

        # Check High >= Close
        invalid_hc = df[df['high'] < df['close']]
        if len(invalid_hc) > 0:
            errors.append(f"Found {len(invalid_hc)} rows where High < Close")

        # Check Low <= Open
        invalid_lo = df[df['low'] > df['open']]
        if len(invalid_lo) > 0:
            errors.append(f"Found {len(invalid_lo)} rows where Low > Open")

        # Check Low <= Close
        invalid_lc = df[df['low'] > df['close']]
        if len(invalid_lc) > 0:
            errors.append(f"Found {len(invalid_lc)} rows where Low > Close")

        # Check for negative prices
        for col in required_columns:
            negative = df[df[col] < 0]
            if len(negative) > 0:
                errors.append(f"Found {len(negative)} negative values in {col}")

        # Check for zero prices
        for col in required_columns:
            zeros = df[df[col] == 0]
            if len(zeros) > 0:
                errors.append(f"Found {len(zeros)} zero values in {col}")

        is_valid = len(errors) == 0

        if is_valid:
            logger.info("✅ OHLC data validation passed")
        else:
            logger.warning(f"❌ OHLC data validation failed: {len(errors)} issues found")
            for error in errors:
                logger.warning(f"  - {error}")

        return is_valid, errors

    @staticmethod
    def detect_missing_data(df: pd.DataFrame, date_column: str = 'date') -> Dict:
        """
        Detect missing data in time series

        Args:
            df: DataFrame with datetime index or date column
            date_column: Name of date column (if not index)

        Returns:
            Dictionary with missing data statistics
        """
        # Ensure datetime index
        if date_column in df.columns:
            df = df.set_index(date_column)

        # Check for NaN values
        nan_counts = df.isna().sum()
        total_nans = nan_counts.sum()

        # Check for missing dates (gaps in time series)
        if isinstance(df.index, pd.DatetimeIndex):
            date_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
            missing_dates = date_range.difference(df.index)
            missing_date_count = len(missing_dates)
        else:
            missing_dates = []
            missing_date_count = 0

        result = {
            'total_rows': len(df),
            'total_nans': int(total_nans),
            'nan_by_column': nan_counts.to_dict(),
            'missing_dates': missing_date_count,
            'missing_date_list': missing_dates.tolist() if len(missing_dates) < 10 else missing_dates[:10].tolist(),
            'data_quality_pct': round((1 - total_nans / (len(df) * len(df.columns))) * 100, 2)
        }

        logger.info(f"Missing Data Analysis:")
        logger.info(f"  - Total rows: {result['total_rows']}")
        logger.info(f"  - Total NaNs: {result['total_nans']}")
        logger.info(f"  - Missing dates: {result['missing_dates']}")
        logger.info(f"  - Data quality: {result['data_quality_pct']}%")

        return result

    @staticmethod
    def detect_outliers(df: pd.DataFrame, column: str, method: str = 'iqr',
                       threshold: float = 3.0) -> pd.Series:
        """
        Detect outliers in data

        Args:
            df: DataFrame
            column: Column to check
            method: 'iqr' or 'zscore'
            threshold: Threshold for outlier detection

        Returns:
            Boolean series indicating outliers
        """
        if column not in df.columns:
            logger.warning(f"Column {column} not found")
            return pd.Series([False] * len(df))

        data = df[column].dropna()

        if method == 'iqr':
            # Interquartile Range method
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            outliers = (df[column] < lower_bound) | (df[column] > upper_bound)

        elif method == 'zscore':
            # Z-score method
            mean = data.mean()
            std = data.std()
            z_scores = np.abs((df[column] - mean) / std)
            outliers = z_scores > threshold

        else:
            logger.error(f"Unknown outlier detection method: {method}")
            return pd.Series([False] * len(df))

        outlier_count = outliers.sum()
        outlier_pct = (outlier_count / len(df)) * 100

        logger.info(f"Outlier Detection ({method}) for {column}:")
        logger.info(f"  - Found {outlier_count} outliers ({outlier_pct:.2f}%)")

        return outliers

    @staticmethod
    def fill_missing_data(df: pd.DataFrame, method: str = 'forward',
                         limit: Optional[int] = None) -> pd.DataFrame:
        """
        Fill missing data

        Args:
            df: DataFrame with missing data
            method: 'forward', 'backward', 'interpolate', or 'mean'
            limit: Maximum number of consecutive NaNs to fill

        Returns:
            DataFrame with filled data
        """
        df_filled = df.copy()

        if method == 'forward':
            df_filled = df_filled.fillna(method='ffill', limit=limit)
        elif method == 'backward':
            df_filled = df_filled.fillna(method='bfill', limit=limit)
        elif method == 'interpolate':
            df_filled = df_filled.interpolate(method='linear', limit=limit)
        elif method == 'mean':
            df_filled = df_filled.fillna(df.mean())
        else:
            logger.error(f"Unknown fill method: {method}")
            return df

        filled_count = df.isna().sum().sum() - df_filled.isna().sum().sum()
        logger.info(f"Filled {filled_count} missing values using {method} method")

        return df_filled

    @staticmethod
    def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None,
                         keep: str = 'first') -> pd.DataFrame:
        """
        Remove duplicate rows

        Args:
            df: DataFrame
            subset: Columns to consider for duplicates
            keep: 'first', 'last', or False (remove all)

        Returns:
            DataFrame without duplicates
        """
        initial_count = len(df)
        df_clean = df.drop_duplicates(subset=subset, keep=keep)
        removed_count = initial_count - len(df_clean)

        if removed_count > 0:
            logger.warning(f"Removed {removed_count} duplicate rows")
        else:
            logger.info("No duplicate rows found")

        return df_clean

    @staticmethod
    def validate_price_changes(df: pd.DataFrame, column: str = 'close',
                              max_change_pct: float = 10.0) -> pd.Series:
        """
        Detect abnormal price changes (potential errors)

        Args:
            df: DataFrame with price data
            column: Price column to check
            max_change_pct: Maximum normal price change percentage

        Returns:
            Boolean series indicating abnormal changes
        """
        if column not in df.columns:
            logger.warning(f"Column {column} not found")
            return pd.Series([False] * len(df))

        # Calculate percentage change
        pct_change = df[column].pct_change().abs() * 100

        # Detect abnormal changes
        abnormal = pct_change > max_change_pct

        abnormal_count = abnormal.sum()
        if abnormal_count > 0:
            logger.warning(f"Found {abnormal_count} abnormal price changes (>{max_change_pct}%)")
            # Log some examples
            examples = df[abnormal][[column]].head()
            for idx, row in examples.iterrows():
                change = pct_change.loc[idx]
                logger.warning(f"  - {idx}: {change:.2f}% change")
        else:
            logger.info(f"All price changes within normal range (<{max_change_pct}%)")

        return abnormal

    @staticmethod
    def clean_data(df: pd.DataFrame, fill_method: str = 'forward',
                  remove_outliers: bool = False) -> pd.DataFrame:
        """
        Complete data cleaning pipeline

        Args:
            df: Raw DataFrame
            fill_method: Method to fill missing data
            remove_outliers: Whether to remove outliers

        Returns:
            Cleaned DataFrame
        """
        logger.info("Starting data cleaning pipeline...")

        df_clean = df.copy()

        # 1. Remove duplicates
        df_clean = DataQualityChecker.remove_duplicates(df_clean)

        # 2. Validate OHLC (if applicable)
        if all(col in df_clean.columns for col in ['open', 'high', 'low', 'close']):
            is_valid, errors = DataQualityChecker.validate_ohlc(df_clean)
            if not is_valid:
                logger.warning("OHLC validation failed, but continuing with cleaning")

        # 3. Detect and report missing data
        missing_info = DataQualityChecker.detect_missing_data(df_clean)

        # 4. Fill missing data
        if missing_info['total_nans'] > 0:
            df_clean = DataQualityChecker.fill_missing_data(df_clean, method=fill_method)

        # 5. Handle outliers (if requested)
        if remove_outliers:
            for col in df_clean.select_dtypes(include=[np.number]).columns:
                outliers = DataQualityChecker.detect_outliers(df_clean, col)
                if outliers.sum() > 0:
                    # Replace outliers with interpolated values
                    df_clean.loc[outliers, col] = np.nan
                    df_clean[col] = df_clean[col].interpolate()

        logger.info("✅ Data cleaning pipeline complete")

        return df_clean

    @staticmethod
    def generate_quality_report(df: pd.DataFrame) -> Dict:
        """
        Generate comprehensive data quality report

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary with quality metrics
        """
        report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'date_range': {
                'start': str(df.index.min()) if isinstance(df.index, pd.DatetimeIndex) else 'N/A',
                'end': str(df.index.max()) if isinstance(df.index, pd.DatetimeIndex) else 'N/A'
            },
            'missing_data': DataQualityChecker.detect_missing_data(df),
            'duplicates': len(df) - len(df.drop_duplicates()),
            'columns': list(df.columns)
        }

        # OHLC validation
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            is_valid, errors = DataQualityChecker.validate_ohlc(df)
            report['ohlc_valid'] = is_valid
            report['ohlc_errors'] = errors

        # Outliers for numeric columns
        outlier_summary = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            outliers = DataQualityChecker.detect_outliers(df, col)
            outlier_summary[col] = int(outliers.sum())
        report['outliers'] = outlier_summary

        logger.info("=" * 60)
        logger.info("DATA QUALITY REPORT")
        logger.info("=" * 60)
        logger.info(f"Total Rows: {report['total_rows']}")
        logger.info(f"Total Columns: {report['total_columns']}")
        logger.info(f"Date Range: {report['date_range']['start']} to {report['date_range']['end']}")
        logger.info(f"Data Quality: {report['missing_data']['data_quality_pct']}%")
        logger.info(f"Duplicates: {report['duplicates']}")
        if 'ohlc_valid' in report:
            logger.info(f"OHLC Valid: {report['ohlc_valid']}")
        logger.info("=" * 60)

        return report


if __name__ == "__main__":
    print("Data Quality Checker Test")
    print("=" * 70)

    # Create sample data with various quality issues
    dates = pd.date_range('2024-01-01', periods=100, freq='D')

    # Simulate price data with issues
    np.random.seed(42)
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)

    df = pd.DataFrame({
        'date': dates,
        'open': close_prices + np.random.randn(100) * 0.5,
        'high': close_prices + abs(np.random.randn(100)) * 2,
        'low': close_prices - abs(np.random.randn(100)) * 2,
        'close': close_prices,
        'volume': np.random.randint(1000000, 5000000, 100)
    })

    # Introduce some quality issues
    df.loc[10, 'close'] = np.nan  # Missing data
    df.loc[20, 'high'] = df.loc[20, 'low'] - 1  # Invalid OHLC (high < low)
    df.loc[30, 'close'] = df.loc[30, 'close'] * 1.5  # Outlier (50% jump)
    df = pd.concat([df, df.iloc[50:51]])  # Duplicate row

    df = df.set_index('date')

    print("\n1. OHLC Validation")
    print("-" * 70)
    is_valid, errors = DataQualityChecker.validate_ohlc(df)
    print(f"Valid: {is_valid}")
    if errors:
        print("Errors found:")
        for error in errors:
            print(f"  - {error}")

    print("\n2. Missing Data Detection")
    print("-" * 70)
    missing_info = DataQualityChecker.detect_missing_data(df)
    print(f"Total NaNs: {missing_info['total_nans']}")
    print(f"Data Quality: {missing_info['data_quality_pct']}%")

    print("\n3. Outlier Detection")
    print("-" * 70)
    outliers = DataQualityChecker.detect_outliers(df, 'close', method='iqr')
    print(f"Outliers found: {outliers.sum()}")

    print("\n4. Price Change Validation")
    print("-" * 70)
    abnormal = DataQualityChecker.validate_price_changes(df, 'close', max_change_pct=10.0)
    print(f"Abnormal changes: {abnormal.sum()}")

    print("\n5. Complete Data Cleaning")
    print("-" * 70)
    df_clean = DataQualityChecker.clean_data(df, fill_method='forward', remove_outliers=True)
    print(f"Cleaned data shape: {df_clean.shape}")

    print("\n6. Quality Report")
    print("-" * 70)
    report = DataQualityChecker.generate_quality_report(df_clean)
    print(f"Overall Data Quality: {report['missing_data']['data_quality_pct']}%")

    print("\n" + "=" * 70)
    print("✅ Data Quality Checker Working Successfully!")
    print("=" * 70)

    print("\nFeatures Available:")
    print("  1. OHLC Validation - Ensure High >= Low, etc.")
    print("  2. Missing Data Detection - Find NaNs and gaps")
    print("  3. Outlier Detection - IQR or Z-score methods")
    print("  4. Data Filling - Forward, backward, interpolate")
    print("  5. Duplicate Removal - Clean duplicate rows")
    print("  6. Price Change Validation - Detect abnormal moves")
    print("  7. Complete Cleaning Pipeline - All-in-one")
    print("  8. Quality Report - Comprehensive analysis")

    print("\nReady for data pipeline integration! 🚀")
