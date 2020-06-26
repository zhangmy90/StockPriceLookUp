from flask import Flask, render_template, request, redirect
from datetime import datetime
import pandas as pd
from pandas import DataFrame, Series

import numpy as np

import bokeh
from bokeh.embed import components
from bokeh.plotting import figure, output_file, show

from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool

from key import key
import pprint


import requests

app = Flask(__name__)
app.vars = {}

@app.route('/')
def main():
    return redirect('/index')

@app.route('/index',methods=['GET','POST'])
def index():
  if request.method == 'GET':
    return render_template('index.html')
  else:
    # request was a POST
    ticker = request.form["ticker"].upper()
    # Create data frame for the ticker (request with API key)
    df = stock_info(ticker)
      
    # for request sent from checkboxes
    open = request.form.get("open")
    print('open=', open)
   
    inputs = {}
    variables = []
    for checkbox in 'open', 'close', 'adjusted_close', 'volume':
      value = request.form.get(checkbox)
      if value:
        inputs[checkbox] = checkbox
        variables.append(checkbox)
    variables = list(set(variables))
    columns = [inputs[checkbox] for checkbox in variables] 
     
    script, div = plot1(df, ticker, columns)
      
    column = request.form["column"]
    # If none of the checkbox is selected
    if not variables:
      if column not in ('open', 'close', 'adjusted_close', 'volume'):
        return render_template('index.html')
       
      else:
        script, div = plot2(df, ticker, column)      
    return render_template('graph.html', script = script, div = div, ticker = ticker)

if __name__ == '__main__':
  app.run(port=33507)


def stock_info(ticker):
    url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={}&apikey={}'.format(ticker, key)
    r = requests.get(url)

    if r.status_code != 200:
      error = 'Invalid ticker token'
      return error
    else: 
      # print(r.status_code) # 200 (succeeded)
      # pprint.pprint(r.json())
      # normalize semi-structure JSON data into a flat table
      json_response = r.json()

      # df = pd.DataFrame(json_response['Time Series (Daily)']).T
      df = pd.DataFrame.from_dict(json_response['Time Series (Daily)'], orient = 'index')
      df = df.reset_index()
      df = df.rename(index=str, columns={
        "index": "date", 
        "1. open": "open",
        "2. high": "high", 
        "3. low": "low", 
        "4. close": "close", 
        "5. adjusted close": "adjusted_close", 
        "6. volume": "volume", 
        "7. dividend amount": "dividend_amount", 
        "8. split coefficient": "split_coefficient"})
      df = df.drop(columns = ['split_coefficient'])

      # change to datetime
      df['date'] = pd.to_datetime(df['date'])

      #Sort data according to date
      df = df.sort_values(by=['date'])

      # Convert to float type
      for i in list(df.columns):
          if i != 'date':
              df[i] = df[i].astype('float')
      
      
      return df


def plot1(df, ticker, columns, hover_tool = None):
    select_tools = ['box_select', 'lasso_select', 'poly_select', 'tap', 'reset', 'redo', 'save']
    
    # columns = ['open', 'high', 'low', 'close', 'adjusted_close']
    len_col = len(columns)
    color = ['red', 'blue', 'green', 'pink', 'orange', 'black', 'purple', 'grey']
    x_axis= df["date"]
    legend = ["--".join([ticker,column]) for column in columns]
  
    data = {'xs': [x_axis] * len_col, 
            'ys': [df[column].values for column in columns],
            'color': color[:len_col],
            'legend': legend[:len_col]}
    # Create a ColumnDataSource object
    source = ColumnDataSource(data)

    p = figure(title=ticker, x_axis_type = "datetime", plot_height=600, plot_width=800, tools = select_tools)
    p.title.align = "center"
    p.title.text_font_size = "20px"
    p.xaxis.axis_label = 'Time'
    p.yaxis.axis_label = 'Price (USD)'
    p.background_fill_color="#f5f5f5"
    p.multi_line(xs='xs', ys='ys', line_color = 'color', legend = 'legend', source=source)   
    
    tool_tips = []
    for column in columns:
      tool_tips.append((str(column), "@ys"))
    p.add_tools(HoverTool(show_arrow = False, line_policy='next', tooltips=tool_tips))
    script, div = components(p)
    return script, div

def datetime(x):
    return np.array(x, dtype=np.datetime64)

def plot2(df, ticker, column):
    select_tools = ['box_select', 'lasso_select', 'poly_select', 'tap', 'reset', 'redo','save']

    if column in df.columns:

      d ={
        'dates': df['date'],
        'price': df[column],
        'volume': df['volume']
      }

      df = pd.DataFrame(data = d)
      df['date'] = pd.to_datetime(df['dates'], unit='us')

      p = figure(title = "--".join([ticker,column]), 
                  x_axis_type = "datetime", 
                  x_axis_label = 'Time',
                  y_axis_label = 'Price (USD)',
                  plot_height = 600, plot_width = 800,
                  toolbar_location = 'below',
                  tools = select_tools)

      p.title.align = "center"
      p.title.text_font_size = "20px"
      p.grid.grid_line_color="white"
      p.background_fill_color="#f5f5f5"
      p.axis.axis_line_color = None
      p.line(x='date', y = 'price', source = df, line_width=2, line_color = 'orange')
      
      tooltips = [
        ('Date', '@date{%Y%m%d %H:%M}'),
        ('Stock Price', "@price"),
        ('Volume', "@volume")
      ]

      formatters = {
        'date': 'datetime',
        'price': 'printf',
        'volume': 'printf',
      }
      p.add_tools(HoverTool(tooltips = tooltips, formatters=formatters, mode='vline')) #, formatters, mode='vline'))
      script, div = components(p)
      return script, div
