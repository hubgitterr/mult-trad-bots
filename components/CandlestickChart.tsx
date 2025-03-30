'use client';

import React from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, Tooltip, Legend, TimeScale } from 'chart.js';
import { CandlestickController, CandlestickElement, OhlcController, OhlcElement } from 'chartjs-chart-financial';
import { Chart } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns'; // Import the adapter

// Register necessary Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  CandlestickController,
  CandlestickElement,
  OhlcController,
  OhlcElement,
  Tooltip,
  Legend,
  TimeScale // Register TimeScale for time-based x-axis
);

interface CandlestickChartProps {
  chartData: {
    symbol: string;
    interval: string;
    klines: (string | number)[][];
  };
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({ chartData }) => {
  if (!chartData || !chartData.klines || chartData.klines.length === 0) {
    return <p>No data available for chart.</p>;
  }

  // Transform kline data into the format required by chartjs-chart-financial
  // { x: open_time, o: open, h: high, l: low, c: close }
  const data = chartData.klines.map(kline => ({
    x: kline[0] as number, // Open time (timestamp)
    o: parseFloat(kline[1] as string), // Open price
    h: parseFloat(kline[2] as string), // High price
    l: parseFloat(kline[3] as string), // Low price
    c: parseFloat(kline[4] as string), // Close price
  }));

  const options = {
    responsive: true,
    maintainAspectRatio: false, // Allow chart to fill container height
     scales: {
       x: {
         type: 'timeseries' as const, // Correct type for time-based axis
         time: {
           unit: 'hour' as const, // Adjust unit based on interval (e.g., 'day', 'minute')
          tooltipFormat: 'PPpp', // Format for tooltip display (requires date-fns)
        },
        title: {
          display: true,
          text: 'Time',
        },
        ticks: {
          source: 'auto' as const, // Automatically determine ticks
          maxRotation: 0,
          autoSkip: true,
        }
      },
      y: {
        title: {
          display: true,
          text: `Price (${chartData.symbol})`,
        },
        ticks: {
            // Consider adding formatting for currency if needed
            // callback: function(value, index, values) {
            //     return '$' + value;
            // }
        }
      },
    },
    plugins: {
      legend: {
        display: false, // Candlestick charts usually don't need a legend
      },
      tooltip: {
        mode: 'index' as const,
         intersect: false,
       },
     },
     // parsing: false, // Removed to resolve TS error; data is pre-parsed
   };

  const chartConfig = {
    datasets: [
      {
        label: `${chartData.symbol} Price`,
        data: data,
        // type: 'candlestick', // Type is inferred by controller registration
      },
    ],
  };

  return (
    <div className="relative h-96"> {/* Set a height for the chart container */}
      <Chart type='candlestick' options={options} data={chartConfig} />
    </div>
  );
};

export default CandlestickChart;
