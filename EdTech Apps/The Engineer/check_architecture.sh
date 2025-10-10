#!/bin/bash
# Architecture Verification Script for The Engineer Build

echo "=== Architecture Verification ==="
echo ""

echo "Host system:"
echo "  Architecture: $(uname -m)"
echo "  OS: $(uname -s)"
echo ""

if command -v docker &> /dev/null; then
    echo "Docker status:"
    if docker info &> /dev/null; then
        echo "  ✅ Docker is running"
        
        echo "  Testing x86_64 emulation..."
        if docker run --rm --platform linux/amd64 alpine:latest uname -m 2>/dev/null | grep -q "x86_64"; then
            echo "  ✅ x86_64 emulation works"
            echo "  📦 Ready to build Linux x86_64 executables"
        else
            echo "  ❌ x86_64 emulation failed"
            echo "  💡 Install Docker Desktop and enable containerd"
        fi
    else
        echo "  ❌ Docker is not running"
    fi
else
    echo "Docker status:"
    echo "  ❌ Docker not installed"
fi

echo ""
echo "Target for The Engineer:"
echo "  🎯 Linux x86_64 (amd64) - for Linux Mint laptops"
echo "  📁 Output: dist/Engineer-linux-1.0.0.tar.gz"
echo "" 