#!/bin/bash
# 强制升级pip到最新版（绕过Streamlit Cloud的pip版本限制）
pip install --upgrade pip==26.0.1
# 安装依赖
pip install -r requirements.txt