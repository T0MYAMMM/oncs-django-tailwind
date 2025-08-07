import React, { useState, useEffect } from 'react';
import ReactApexChart from 'react-apexcharts';

function Chart() {
  const sales = JSON.parse(JSON.parse(document.getElementById('sales').textContent));
  const chartData = {};

  sales.forEach(sale => {
    let date = sale.fields.PurchaseDate;
    let ItemName = sale.fields.Product;

    if (!chartData[ItemName]) {
        chartData[ItemName] = {
            count: sale.fields.Quantity,
            date: date
        };
    } else {
        chartData[ItemName].count += sale.fields.Quantity;
    }

  });

  const consolidatedChartData = [];

  for (const data in chartData) {
    consolidatedChartData.push({
      x: chartData[data].date,
      product: data,
      y: chartData[data].count,
      date: chartData[data].date
    });
  }

  consolidatedChartData.sort((a, b) => (a.x > b.x) ? 1 : ((b.x > a.x) ? -1 : 0));


  const options = {
    chart: {
      height: 250,
      type: 'bar',
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: '55%',
        endingShape: 'rounded',
      },
    },
    dataLabels: {
      enabled: true,
      offsetY: -20,
      style: {
        fontSize: '12px',
        colors: consolidatedChartData.map((color) => '#546E7A'),
      },
    },
    xaxis: {
      categories: consolidatedChartData.map((cat) => cat.date),
      labels: {
        style: {
          colors: '#546E7A',
          fontWeight: 500,
        },
      },
    },
    colors: ['#546E7A'],
  };

  const series = [
    {
      name: 'Product Sales',
      data: consolidatedChartData.map((data) => data.y),
    },
  ];

  let trafficChannelsChartColors = {};
  if (document.documentElement.classList.contains('dark')) {
    trafficChannelsChartColors = {
      strokeColor: '#1f2937'
    };
  } else {
    trafficChannelsChartColors = {
      strokeColor: '#ffffff'
    };
  }

  const donutOptions = {
    chart: {
      height: 250, 
      type: 'donut',
      fontFamily: 'Inter, sans-serif',
      toolbar: {
        show: false
      },
    },
    colors: ['#16BDCA', '#FDBA8C', '#1A56DB', '#FF4500', '#32CD32', '#C70039', '#007FFF', '#FFFF00', '#808080', '#DC143C', '#000000', '#FFFFFF'],
    responsive: [{
      breakpoint: 430,
      options: {
        chart: {
          height: 200 
        }
      }
    }],
    stroke: {
      colors: [trafficChannelsChartColors.strokeColor]
    },
    states: {
      hover: {
        filter: {
          type: 'darken',
          value: 0.9
        }
      }
    },
    tooltip: {
      shared: true,
      followCursor: false,
      fillSeriesColor: false,
      inverseOrder: true,
      style: {
        fontSize: '14px',
        fontFamily: 'Inter, sans-serif'
      },
      x: {
        show: true,
        formatter: function (_, { seriesIndex, w }) {
          const label = w.config.labels[seriesIndex];
          return label;
        }
      },
      y: {
        formatter: function (value) {
          return value;
        }
      }
    },
    grid: {
      show: false
    },
    dataLabels: {
      enabled: false
    },
    legend: {
      show: false
    },
  };

  const donutSeries = consolidatedChartData.map((data) => data.y);

  return (
    <div className="md:flex">
      <div className="w-full md:w-1/2">
        <div id="chart1">
          <ReactApexChart options={options} series={series} type="bar"  />
        </div>
      </div>
      <div className="w-full md:w-1/2">
        <div id="chart2">
          <ReactApexChart options={donutOptions} series={donutSeries} type="donut"  />
        </div>
      </div>
    </div>
  );
}

export default Chart;
