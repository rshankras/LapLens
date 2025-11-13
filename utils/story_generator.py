"""
Story generation utilities for creating race narratives.
Transforms telemetry data into compelling, human-readable stories.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
from config import config


class RaceStoryGenerator:
    """Generates narrative stories from telemetry and lap data."""

    def __init__(self, track_name: str = "Unknown Track"):
        """
        Initialize the story generator.

        Args:
            track_name: Name of the track for context
        """
        self.track_name = track_name

    def generate_session_narrative(
        self,
        telemetry: pd.DataFrame,
        lap_times: pd.DataFrame,
        sector_times: pd.DataFrame,
        vehicle_id: str
    ) -> Dict:
        """
        Generate complete session narrative with insights and recommendations.

        Args:
            telemetry: Full telemetry DataFrame
            lap_times: Lap time statistics DataFrame
            sector_times: Sector time statistics DataFrame
            vehicle_id: Vehicle identifier

        Returns:
            Dictionary containing complete story with all components
        """
        # Analyze components
        trajectory = self.analyze_performance_trajectory(lap_times)
        breakthrough = self.identify_breakthrough_moments(lap_times, telemetry)
        consistency = self.calculate_consistency_score(lap_times)
        risk = self.calculate_risk_index(telemetry)
        sector_insights = self.generate_sector_narrative(sector_times)
        optimal = self.find_optimal_lap(lap_times, sector_times)
        recommendations = self.generate_recommendations(
            lap_times, sector_times, telemetry, trajectory, consistency, risk
        )

        # Generate executive summary
        executive_summary = self._create_executive_summary(
            vehicle_id, lap_times, trajectory, breakthrough, consistency
        )

        # Generate detailed narrative
        detailed_narrative = self._create_detailed_narrative(
            vehicle_id, lap_times, trajectory, breakthrough, consistency, risk
        )

        return {
            "title": f"Race Story: {self.track_name} - {vehicle_id}",
            "executive_summary": executive_summary,
            "detailed_narrative": detailed_narrative,
            "performance_trajectory": trajectory,
            "breakthrough_moment": breakthrough,
            "consistency_score": consistency,
            "risk_index": risk,
            "sector_insights": sector_insights,
            "optimal_lap": optimal,
            "recommendations": recommendations,
            "technical_insights": self._generate_technical_insights(
                telemetry, lap_times
            )
        }

    def analyze_performance_trajectory(self, lap_times: pd.DataFrame) -> Dict:
        """
        Analyze overall performance trend across the session.

        Args:
            lap_times: Lap time statistics

        Returns:
            Dictionary with trajectory analysis
        """
        if len(lap_times) < 3:
            return {
                "trend": "insufficient_data",
                "narrative": "Not enough laps for trend analysis.",
                "slope": 0,
                "improvement_rate": 0
            }

        # Calculate trend using linear regression on lap times
        laps = lap_times['lap'].values
        times = lap_times['lap_time'].values

        # Simple linear regression
        slope = np.polyfit(laps, times, 1)[0]

        # Categorize trend
        if slope < -0.1:
            trend = "improving"
            trend_desc = "consistent improvement"
        elif slope > 0.1:
            trend = "declining"
            trend_desc = "gradual decline"
        else:
            trend = "consistent"
            trend_desc = "steady consistency"

        # Calculate improvement rate (seconds per lap)
        improvement_rate = abs(slope)

        # Find fastest stint (3+ consecutive laps)
        fastest_stint = self._find_fastest_stint(lap_times)

        # Generate narrative
        narrative = self._create_trajectory_narrative(
            trend, trend_desc, improvement_rate, fastest_stint, lap_times
        )

        return {
            "trend": trend,
            "narrative": narrative,
            "slope": slope,
            "improvement_rate": improvement_rate,
            "fastest_stint": fastest_stint
        }

    def identify_breakthrough_moments(
        self,
        lap_times: pd.DataFrame,
        telemetry: pd.DataFrame
    ) -> Optional[Dict]:
        """
        Identify breakthrough moments where significant improvement occurred.

        Args:
            lap_times: Lap time statistics
            telemetry: Full telemetry data

        Returns:
            Dictionary with breakthrough moment details or None
        """
        if len(lap_times) < 2:
            return None

        # Find lap with biggest improvement
        lap_times_sorted = lap_times.sort_values('lap')
        lap_times_sorted['improvement'] = lap_times_sorted['lap_time'].diff() * -1

        # Breakthrough is improvement > 0.3s
        breakthroughs = lap_times_sorted[lap_times_sorted['improvement'] > 0.3]

        if len(breakthroughs) == 0:
            # No major breakthrough, but find best lap
            best_lap_idx = lap_times['lap_time'].idxmin()
            best_lap = lap_times.loc[best_lap_idx]

            return {
                "lap": int(best_lap['lap']),
                "type": "best_lap",
                "improvement": 0.0,
                "narrative": f"Best lap achieved on Lap {int(best_lap['lap'])} with a time of {best_lap['lap_time']:.3f}s.",
                "impact": "Set session benchmark."
            }

        # Get first major breakthrough
        breakthrough = breakthroughs.iloc[0]
        lap_num = int(breakthrough['lap'])
        improvement = breakthrough['improvement']

        # Analyze what changed in breakthrough lap
        changes = self._analyze_lap_changes(lap_num, telemetry)

        narrative = self._create_breakthrough_narrative(
            lap_num, improvement, changes
        )

        return {
            "lap": lap_num,
            "type": "breakthrough",
            "improvement": improvement,
            "narrative": narrative,
            "changes": changes,
            "impact": f"Gained {improvement:.3f}s in single lap."
        }

    def calculate_consistency_score(self, lap_times: pd.DataFrame) -> Dict:
        """
        Calculate consistency score (0-10 scale).

        Args:
            lap_times: Lap time statistics

        Returns:
            Dictionary with consistency metrics
        """
        if len(lap_times) < 3:
            return {
                "score": 0.0,
                "rating": "N/A",
                "std_dev": 0.0,
                "range": 0.0
            }

        times = lap_times['lap_time'].values
        mean_time = np.mean(times)
        std_dev = np.std(times)
        time_range = np.max(times) - np.min(times)

        # Score: 10 = perfect consistency (0 std dev)
        # Lower scores for higher variation
        # Normalize by mean time (coefficient of variation)
        cv = (std_dev / mean_time) * 100  # Coefficient of variation as percentage

        # Score mapping (more realistic for amateur racing):
        # cv < 0.5% = 10 (pro-level)
        # cv = 1% = 9 (excellent)
        # cv = 2% = 7.5 (very good)
        # cv = 5% = 5 (fair)
        # cv = 10% = 2.5 (needs improvement)
        # cv > 15% = 0 (poor)

        if cv < 0.5:
            score = 10.0
        elif cv < 2.0:
            # Smooth decline from 10 to 7.5
            score = 10.0 - (cv - 0.5) * (2.5 / 1.5)
        elif cv < 10.0:
            # Linear decline from 7.5 to 2.5
            score = 7.5 - (cv - 2.0) * (5.0 / 8.0)
        else:
            # Linear decline from 2.5 to 0 (cv 10-15%)
            score = max(0.0, 2.5 - (cv - 10.0) * (2.5 / 5.0))

        # Rating
        if score >= 8.5:
            rating = "Excellent"
        elif score >= 7.0:
            rating = "Very Good"
        elif score >= 5.5:
            rating = "Good"
        elif score >= 4.0:
            rating = "Fair"
        else:
            rating = "Needs Improvement"

        return {
            "score": round(score, 1),
            "rating": rating,
            "std_dev": round(std_dev, 3),
            "range": round(time_range, 3),
            "coefficient_of_variation": round(cv, 2)
        }

    def calculate_risk_index(self, telemetry: pd.DataFrame) -> Dict:
        """
        Calculate risk-taking index (0-10 scale).

        Args:
            telemetry: Full telemetry DataFrame

        Returns:
            Dictionary with risk metrics
        """
        if len(telemetry) == 0:
            return {
                "score": 0.0,
                "rating": "N/A",
                "components": {}
            }

        components = {}

        # Braking aggression (40% weight)
        if 'brake_intensity' in telemetry.columns:
            heavy_braking_pct = (
                (telemetry['brake_intensity'] > config.HEAVY_BRAKE_THRESHOLD).sum()
                / len(telemetry) * 100
            )
            brake_score = min(10.0, heavy_braking_pct * 2)  # Scale to 0-10
            components['braking_aggression'] = brake_score
        else:
            brake_score = 5.0  # Default

        # Throttle aggression (30% weight)
        if 'ath' in telemetry.columns:
            full_throttle_pct = (
                (telemetry['ath'] > config.THROTTLE_FULL_THRESHOLD).sum()
                / len(telemetry) * 100
            )
            throttle_score = min(10.0, full_throttle_pct / 5)  # Scale to 0-10
            components['throttle_aggression'] = throttle_score
        else:
            throttle_score = 5.0  # Default

        # Corner speed variance (30% weight)
        if 'Speed' in telemetry.columns:
            speed_cv = (telemetry['Speed'].std() / telemetry['Speed'].mean()) * 100
            corner_score = min(10.0, speed_cv / 2)  # Scale to 0-10
            components['corner_variance'] = corner_score
        else:
            corner_score = 5.0  # Default

        # Calculate weighted risk index
        risk_score = (
            brake_score * 0.4 +
            throttle_score * 0.3 +
            corner_score * 0.3
        )

        # Rating
        if risk_score >= 8.0:
            rating = "Very Aggressive"
        elif risk_score >= 6.5:
            rating = "Aggressive"
        elif risk_score >= 5.0:
            rating = "Balanced"
        elif risk_score >= 3.5:
            rating = "Conservative"
        else:
            rating = "Very Conservative"

        return {
            "score": round(risk_score, 1),
            "rating": rating,
            "components": components
        }

    def generate_sector_narrative(self, sector_times: pd.DataFrame) -> List[Dict]:
        """
        Generate narrative for each sector's performance.

        Args:
            sector_times: Sector time statistics

        Returns:
            List of sector insight dictionaries
        """
        if len(sector_times) == 0:
            return []

        insights = []

        # Group by sector
        for sector in sector_times['sector'].unique():
            sector_data = sector_times[sector_times['sector'] == sector]

            best_time = sector_data['sector_time'].min()
            worst_time = sector_data['sector_time'].max()
            avg_time = sector_data['sector_time'].mean()
            time_range = worst_time - best_time

            # Determine performance category
            if time_range < 0.1:
                performance = "strength"
                consistency = "excellent"
            elif time_range < 0.3:
                performance = "neutral"
                consistency = "good"
            else:
                performance = "weakness"
                consistency = "inconsistent"

            # Generate narrative
            if performance == "strength":
                narrative = f"{sector} is a strength with {consistency} consistency (range: {time_range:.3f}s)."
            elif performance == "weakness":
                narrative = f"{sector} shows inconsistency with a {time_range:.3f}s range, suggesting improvement potential."
            else:
                narrative = f"{sector} shows {consistency} performance with moderate consistency."

            insights.append({
                "sector": sector,
                "performance": performance,
                "consistency": consistency,
                "best_time": best_time,
                "worst_time": worst_time,
                "avg_time": avg_time,
                "range": time_range,
                "narrative": narrative
            })

        # Sort by performance (weaknesses first for recommendations)
        insights.sort(key=lambda x: x['range'], reverse=True)

        return insights

    def find_optimal_lap(
        self,
        lap_times: pd.DataFrame,
        sector_times: pd.DataFrame
    ) -> Dict:
        """
        Calculate optimal theoretical lap from best sectors.

        Args:
            lap_times: Lap time statistics
            sector_times: Sector time statistics

        Returns:
            Dictionary with optimal lap details
        """
        if len(sector_times) == 0:
            return {
                "optimal_time": None,
                "actual_best": None,
                "potential_gain": 0.0,
                "narrative": "Insufficient data for optimal lap calculation."
            }

        # Find best time for each sector
        best_sectors = sector_times.groupby('sector')['sector_time'].min()
        optimal_time = best_sectors.sum()

        # Get actual best lap
        actual_best = lap_times['lap_time'].min()

        # Calculate potential
        potential_gain = actual_best - optimal_time

        # Find which sectors contribute to the gap
        gap_breakdown = []
        for sector in best_sectors.index:
            sector_data = sector_times[sector_times['sector'] == sector]
            best_sector_time = sector_data['sector_time'].min()

            # Find best lap's time in this sector
            best_lap_num = lap_times.loc[lap_times['lap_time'].idxmin(), 'lap']
            best_lap_sector = sector_data[sector_data['lap'] == best_lap_num]

            if len(best_lap_sector) > 0:
                best_lap_sector_time = best_lap_sector['sector_time'].iloc[0]
                gap = best_lap_sector_time - best_sector_time

                if gap > 0.05:  # Only include meaningful gaps
                    gap_breakdown.append({
                        "sector": sector,
                        "gap": gap
                    })

        # Sort by gap
        gap_breakdown.sort(key=lambda x: x['gap'], reverse=True)

        # Generate narrative
        if potential_gain > 0.1:
            narrative = f"Optimal lap: {optimal_time:.3f}s vs. actual best {actual_best:.3f}s. Potential gain: {potential_gain:.3f}s."
        else:
            narrative = f"Excellent lap construction. Optimal lap ({optimal_time:.3f}s) nearly achieved."

        return {
            "optimal_time": round(optimal_time, 3),
            "actual_best": round(actual_best, 3),
            "potential_gain": round(potential_gain, 3),
            "gap_breakdown": gap_breakdown,
            "narrative": narrative
        }

    def generate_recommendations(
        self,
        lap_times: pd.DataFrame,
        sector_times: pd.DataFrame,
        telemetry: pd.DataFrame,
        trajectory: Dict,
        consistency: Dict,
        risk: Dict
    ) -> List[str]:
        """
        Generate actionable recommendations for improvement.

        Args:
            lap_times: Lap time statistics
            sector_times: Sector time statistics
            telemetry: Full telemetry data
            trajectory: Performance trajectory analysis
            consistency: Consistency metrics
            risk: Risk index metrics

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Sector-based recommendations
        if len(sector_times) > 0:
            sector_insights = self.generate_sector_narrative(sector_times)

            # Focus on weakest sector
            if len(sector_insights) > 0:
                weakest = sector_insights[0]
                if weakest['range'] > 0.3:
                    recommendations.append(
                        f"Focus on {weakest['sector']} consistency - "
                        f"current range of {weakest['range']:.3f}s suggests "
                        f"improvement potential of ~{weakest['range'] * 0.6:.3f}s."
                    )

        # Consistency-based recommendations
        if consistency['score'] < 7.0:
            recommendations.append(
                f"Work on consistency - current score {consistency['score']}/10. "
                f"Reducing lap time variation from {consistency['range']:.3f}s "
                f"to < 0.3s would improve racecraft significantly."
            )

        # Risk-based recommendations
        if risk['score'] > 8.0 and consistency['score'] < 6.0:
            recommendations.append(
                "Aggressive driving style detected with lower consistency. "
                "Consider slightly reducing risk for better overall pace."
            )
        elif risk['score'] < 4.0:
            recommendations.append(
                "Conservative approach noted. Exploring limits in practice "
                "could unlock additional pace."
            )

        # Trajectory-based recommendations
        if trajectory['trend'] == "declining":
            recommendations.append(
                "Pace declining over session - review tire management or "
                "consider earlier sessions for peak performance data."
            )

        # Default recommendation if none generated
        if len(recommendations) == 0:
            recommendations.append(
                "Strong overall performance. Focus on maintaining consistency "
                "while pushing limits in key sectors."
            )

        return recommendations[:3]  # Return top 3

    # Helper methods

    def _find_fastest_stint(self, lap_times: pd.DataFrame, min_laps: int = 3) -> Optional[Dict]:
        """Find fastest consecutive stint of laps."""
        if len(lap_times) < min_laps:
            return None

        lap_times_sorted = lap_times.sort_values('lap')
        best_avg = float('inf')
        best_start = None

        for i in range(len(lap_times_sorted) - min_laps + 1):
            stint = lap_times_sorted.iloc[i:i+min_laps]
            avg_time = stint['lap_time'].mean()

            if avg_time < best_avg:
                best_avg = avg_time
                best_start = int(stint.iloc[0]['lap'])

        if best_start is not None:
            return {
                "start_lap": best_start,
                "end_lap": best_start + min_laps - 1,
                "avg_time": best_avg,
                "laps": min_laps
            }

        return None

    def _analyze_lap_changes(self, lap_num: int, telemetry: pd.DataFrame) -> Dict:
        """Analyze what changed in a specific lap."""
        lap_data = telemetry[telemetry['lap'] == lap_num]

        if len(lap_data) == 0:
            return {}

        changes = {}

        # Braking analysis
        if 'brake_intensity' in lap_data.columns:
            max_brake = lap_data['brake_intensity'].max()
            avg_brake = lap_data['brake_intensity'].mean()
            changes['max_brake_pressure'] = max_brake
            changes['avg_brake_pressure'] = avg_brake

        # Throttle analysis
        if 'ath' in lap_data.columns:
            full_throttle_pct = (lap_data['ath'] > 90).sum() / len(lap_data) * 100
            changes['full_throttle_pct'] = full_throttle_pct

        return changes

    def _create_trajectory_narrative(
        self,
        trend: str,
        trend_desc: str,
        improvement_rate: float,
        fastest_stint: Optional[Dict],
        lap_times: pd.DataFrame
    ) -> str:
        """Create narrative for performance trajectory."""
        total_laps = len(lap_times)

        narrative = f"Across {total_laps} laps, the session showed {trend_desc}"

        if improvement_rate > 0.1:
            narrative += f" at {improvement_rate:.3f}s per lap"

        if fastest_stint:
            narrative += f". Peak performance occurred during laps {fastest_stint['start_lap']}-{fastest_stint['end_lap']}"

        narrative += "."

        return narrative

    def _create_breakthrough_narrative(
        self,
        lap_num: int,
        improvement: float,
        changes: Dict
    ) -> str:
        """Create narrative for breakthrough moment."""
        narrative = f"Breakthrough at Lap {lap_num} with {improvement:.3f}s improvement"

        if 'max_brake_pressure' in changes and changes['max_brake_pressure'] > 70:
            narrative += f". Aggressive braking ({changes['max_brake_pressure']:.0f} bar peak)"

        narrative += " unlocked new pace level."

        return narrative

    def _create_executive_summary(
        self,
        vehicle_id: str,
        lap_times: pd.DataFrame,
        trajectory: Dict,
        breakthrough: Optional[Dict],
        consistency: Dict
    ) -> str:
        """Create 2-3 sentence executive summary."""
        best_lap = lap_times['lap_time'].min()
        avg_lap = lap_times['lap_time'].mean()
        total_laps = len(lap_times)

        summary = f"{vehicle_id} completed {total_laps} laps at {self.track_name} "
        summary += f"with a best time of {best_lap:.3f}s (average: {avg_lap:.3f}s). "

        if breakthrough and breakthrough['type'] == 'breakthrough':
            summary += f"A breakthrough at Lap {breakthrough['lap']} unlocked {breakthrough['improvement']:.3f}s. "

        summary += f"Consistency rated {consistency['rating']} ({consistency['score']}/10)."

        return summary

    def _create_detailed_narrative(
        self,
        vehicle_id: str,
        lap_times: pd.DataFrame,
        trajectory: Dict,
        breakthrough: Optional[Dict],
        consistency: Dict,
        risk: Dict
    ) -> str:
        """Create detailed prose narrative."""
        narrative = f"At {self.track_name}, {vehicle_id} "
        narrative += trajectory['narrative'] + " "

        if breakthrough:
            narrative += breakthrough['narrative'] + " "

        narrative += f"\n\nConsistency was {consistency['rating'].lower()} "
        narrative += f"with a lap time range of {consistency['range']:.3f}s. "

        narrative += f"The driving style was {risk['rating'].lower()} "
        narrative += f"(risk index: {risk['score']}/10)."

        return narrative

    def _generate_technical_insights(
        self,
        telemetry: pd.DataFrame,
        lap_times: pd.DataFrame
    ) -> List[str]:
        """Generate technical insights from telemetry."""
        insights = []

        # Speed insights
        if 'Speed' in telemetry.columns:
            avg_speed = telemetry['Speed'].mean()
            max_speed = telemetry['Speed'].max()
            insights.append(f"Average speed: {avg_speed:.1f} km/h (peak: {max_speed:.1f} km/h)")

        # Braking insights
        if 'brake_intensity' in telemetry.columns:
            max_brake = telemetry['brake_intensity'].max()
            heavy_braking_pct = (telemetry['brake_intensity'] > 50).sum() / len(telemetry) * 100
            insights.append(f"Peak braking: {max_brake:.0f} bar ({heavy_braking_pct:.1f}% heavy braking zones)")

        # G-force insights
        if 'accx_can' in telemetry.columns and 'accy_can' in telemetry.columns:
            max_decel_g = abs(telemetry['accx_can'].min())
            max_lateral_g = telemetry['accy_can'].abs().max()
            insights.append(f"Max braking G-force: {max_decel_g:.2f}g, Max lateral G: {max_lateral_g:.2f}g")

        return insights
