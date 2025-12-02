#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ab1 转 PNG Web 应用 - Flask 后端
"""

import os
import sys
import zipfile
import tempfile
import shutil
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 设置 matplotlib 使用非交互式后端（避免在服务器环境中崩溃）
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

from ab1_to_png import parse_ab1_traces, plot_chromatogram, process_single_file

app = Flask(__name__)
CORS(app)

# 全局异常处理
@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理，防止服务器崩溃"""
    error_detail = traceback.format_exc()
    print(f"未捕获的异常: {error_detail}")
    return jsonify({
        'error': f'服务器内部错误: {str(e)}',
        'detail': str(e)
    }), 500

# 配置
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'ab1', 'abi'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# 创建必要的目录
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files():
    """清理临时文件（可选，用于定期清理）"""
    # 这里可以添加清理逻辑
    pass


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件接口"""
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['file']
    dpi = int(request.form.get('dpi', 200))
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式，请上传 .ab1 或 .abi 文件'}), 400
    
    try:
        # 保存上传的文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 转换文件
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 
                                   Path(filename).with_suffix('.png').name)
        
        success = process_single_file(filepath, app.config['OUTPUT_FOLDER'], dpi=dpi, log_callback=None)
        
        if success:
            return jsonify({
                'success': True,
                'message': '转换成功',
                'filename': Path(filename).with_suffix('.png').name,
                'download_url': f'/api/download/{Path(filename).with_suffix(".png").name}'
            })
        else:
            return jsonify({'error': '文件转换失败'}), 500
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"转换错误: {error_detail}")  # 在服务器端打印详细错误
        return jsonify({
            'error': f'处理文件时出错: {str(e)}',
            'detail': str(e)
        }), 500


@app.route('/api/upload-batch', methods=['POST'])
def upload_batch():
    """批量上传文件接口"""
    if 'files[]' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    files = request.files.getlist('files[]')
    dpi = int(request.form.get('dpi', 200))
    
    if not files or files[0].filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    results = []
    success_count = 0
    
    # 创建临时目录用于批量处理
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            for file in files:
                if file.filename == '':
                    continue
                
                if not allowed_file(file.filename):
                    results.append({
                        'filename': file.filename,
                        'success': False,
                        'error': '不支持的文件格式'
                    })
                    continue
                
                try:
                    # 保存文件
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(temp_dir, filename)
                    file.save(filepath)
                    
                    # 转换文件
                    output_name = Path(filename).with_suffix('.png').name
                    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_name)
                    
                    success = process_single_file(filepath, app.config['OUTPUT_FOLDER'], dpi=dpi, log_callback=None)
                    
                    if success:
                        results.append({
                            'filename': filename,
                            'success': True,
                            'output_name': output_name,
                            'download_url': f'/api/download/{output_name}'
                        })
                        success_count += 1
                    else:
                        results.append({
                            'filename': filename,
                            'success': False,
                            'error': '转换失败'
                        })
                        
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    print(f"处理文件 {file.filename} 时出错: {error_detail}")
                    results.append({
                        'filename': file.filename,
                        'success': False,
                        'error': f'{str(e)}'
                    })
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"批量处理出错: {error_detail}")
        return jsonify({
            'error': f'批量处理失败: {str(e)}',
            'detail': str(e)
        }), 500
    
    return jsonify({
        'success': True,
        'message': f'批量转换完成，成功: {success_count}/{len(results)}',
        'results': results,
        'success_count': success_count,
        'total_count': len(results)
    })


@app.route('/api/download/<filename>')
def download_file(filename):
    """下载转换后的 PNG 文件"""
    try:
        return send_from_directory(
            app.config['OUTPUT_FOLDER'],
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({'error': '文件不存在'}), 404


@app.route('/api/download-all', methods=['POST'])
def download_all():
    """打包下载所有转换后的文件"""
    try:
        data = request.json
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({'error': '没有文件可下载'}), 400
        
        # 创建临时 ZIP 文件
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], 'ab1_converted.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in filenames:
                file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                if os.path.exists(file_path):
                    zipf.write(file_path, filename)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='ab1_converted.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'创建压缩包失败: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'message': '服务运行正常'
    })


if __name__ == '__main__':
    print("=" * 50)
    print("ab1 转 PNG Web 服务启动")
    print("访问 http://localhost:5002 使用工具")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5002)

