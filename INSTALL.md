# 安装说明

## 依赖安装

本项目现在使用**纯Python实现**，**不需要Rust编译**，安装过程更简单快速。

### 当前配置

`requirements.txt` 已配置为使用纯Python版本：
- **uvicorn**: 不使用 `[standard]` 扩展（避免 httptools 和 uvloop 的 Rust 依赖）
- **pydantic v1**: 纯Python实现，无需编译
- **python-jose**: 不使用 cryptography 扩展，使用纯Python实现

### 快速安装

```bash
pip install -r requirements.txt
```

### 性能说明

- 当前配置适合**开发和测试环境**
- 性能较带Rust优化的版本略低，但对于大多数场景已经足够
- 如果需要更高性能，可以考虑使用带Rust优化的版本（需要自行配置）

### 检查是否成功安装

```bash
python3 -c "import pydantic; print(f'Pydantic版本: {pydantic.__version__}')"
```

如果看到版本号（应该是 1.10.13），说明安装成功。

### 常见问题

**Q: 需要安装Rust吗？**
A: 不需要。当前版本使用纯Python实现，无需Rust编译。

**Q: 性能如何？**
A: 纯Python版本性能较带Rust优化的版本略低，但对于大多数应用场景已经足够。如果遇到性能瓶颈，可以考虑使用带Rust优化的版本。

**Q: 安装很慢怎么办？**
A: 使用国内镜像源加速：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

