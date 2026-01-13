"""
시각화 헬퍼 모듈 - 다이어그램 및 스토리보드 시각화 유틸리티
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, FancyBboxPatch
import networkx as nx
import pandas as pd
from typing import Dict, List, Any, Optional
import io
import base64


class DiagramVisualizer:
    """기능 다이어그램 시각화 클래스"""
    
    def __init__(self):
        """초기화"""
        plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows 한글 폰트
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
    
    def create_bubble_diagram(self, facilities: List[Dict[str, Any]], 
                             relationships: List[Dict[str, Any]] = None) -> plt.Figure:
        """
        버블 다이어그램 생성
        
        Args:
            facilities: 시설 정보 리스트 [{'name': '교육동', 'size': 100, 'x': 0.2, 'y': 0.5, 'color': 'blue'}]
            relationships: 관계 정보 리스트 [{'from': '교육동', 'to': '기숙사', 'strength': '강함'}]
        
        Returns:
            matplotlib Figure 객체
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # 시설 버블 그리기
        facility_positions = {}
        for facility in facilities:
            name = facility['name']
            size = facility.get('size', 50)
            x = facility.get('x', 0.5)
            y = facility.get('y', 0.5)
            color = facility.get('color', 'lightblue')
            alpha = facility.get('alpha', 0.7)
            
            # 버블 크기 정규화 (0.05 ~ 0.15 범위)
            normalized_size = 0.05 + (size / max([f.get('size', 50) for f in facilities]) * 0.1)
            
            circle = Circle((x, y), normalized_size, 
                          color=color, alpha=alpha, 
                          edgecolor='black', linewidth=2)
            ax.add_patch(circle)
            
            # 시설명 추가
            ax.text(x, y, name, ha='center', va='center', 
                   fontsize=10, fontweight='bold', wrap=True)
            
            facility_positions[name] = (x, y)
        
        # 관계선 그리기
        if relationships:
            for rel in relationships:
                from_name = rel['from']
                to_name = rel['to']
                strength = rel.get('strength', '중간')
                
                if from_name in facility_positions and to_name in facility_positions:
                    x1, y1 = facility_positions[from_name]
                    x2, y2 = facility_positions[to_name]
                    
                    # 강도에 따른 선 스타일
                    if strength == '강함':
                        linewidth = 3
                        alpha = 0.8
                    elif strength == '중간':
                        linewidth = 2
                        alpha = 0.5
                    else:
                        linewidth = 1
                        alpha = 0.3
                    
                    ax.plot([x1, x2], [y1, y2], 'k-', 
                           linewidth=linewidth, alpha=alpha)
        
        ax.set_title('기능 다이어그램', fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        
        return fig
    
    def create_adjacency_matrix(self, facilities: List[str], 
                               relationships: Dict[str, Dict[str, str]]) -> plt.Figure:
        """
        인접성 매트릭스 생성
        
        Args:
            facilities: 시설명 리스트
            relationships: 관계 딕셔너리 {시설1: {시설2: '강함', 시설3: '중간'}}
        
        Returns:
            matplotlib Figure 객체
        """
        n = len(facilities)
        matrix = [[0 for _ in range(n)] for _ in range(n)]
        
        # 관계 강도 숫자로 변환
        strength_map = {'강함': 3, '중간': 2, '약함': 1, '없음': 0}
        
        for i, fac1 in enumerate(facilities):
            for j, fac2 in enumerate(facilities):
                if i == j:
                    matrix[i][j] = 0  # 자기 자신은 0
                elif fac1 in relationships and fac2 in relationships[fac1]:
                    strength = relationships[fac1][fac2]
                    matrix[i][j] = strength_map.get(strength, 0)
        
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        
        # 축 레이블 설정
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(facilities, rotation=45, ha='right')
        ax.set_yticklabels(facilities)
        
        # 값 표시
        for i in range(n):
            for j in range(n):
                if matrix[i][j] > 0:
                    ax.text(j, i, str(matrix[i][j]), 
                           ha='center', va='center', 
                           color='white' if matrix[i][j] > 1 else 'black',
                           fontweight='bold')
        
        ax.set_title('인접성 매트릭스', fontsize=16, fontweight='bold', pad=20)
        
        # 범례
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('연계 강도 (3: 강함, 2: 중간, 1: 약함)', rotation=270, labelpad=20)
        
        plt.tight_layout()
        return fig
    
    def create_program_diagram(self, program_data: Dict[str, Any]) -> plt.Figure:
        """
        공간 프로그램 다이어그램 생성
        
        Args:
            program_data: 프로그램 데이터 {
                'facilities': [...],
                'groupings': {...},
                'priorities': [...]
            }
        
        Returns:
            matplotlib Figure 객체
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # 왼쪽: 기능별 그룹핑
        if 'groupings' in program_data:
            groupings = program_data['groupings']
            y_pos = 0
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
            
            for i, (group_name, facilities) in enumerate(groupings.items()):
                color = colors[i % len(colors)]
                height = len(facilities) * 0.3
                
                rect = FancyBboxPatch((0.1, y_pos), 0.8, height,
                                     boxstyle="round,pad=0.02",
                                     facecolor=color, alpha=0.7,
                                     edgecolor='black', linewidth=2)
                ax1.add_patch(rect)
                
                ax1.text(0.5, y_pos + height/2, group_name,
                        ha='center', va='center',
                        fontsize=12, fontweight='bold')
                
                # 시설명 표시
                for j, facility in enumerate(facilities):
                    ax1.text(0.5, y_pos + (j+0.5) * 0.3, facility,
                           ha='center', va='center', fontsize=9)
                
                y_pos += height + 0.1
            
            ax1.set_xlim(0, 1)
            ax1.set_ylim(0, y_pos)
            ax1.set_title('기능별 그룹핑', fontsize=14, fontweight='bold')
            ax1.axis('off')
        
        # 오른쪽: 배치 우선순위
        if 'priorities' in program_data:
            priorities = program_data['priorities']
            y_positions = range(len(priorities))
            
            ax2.barh(y_positions, [p['priority'] for p in priorities],
                    color='skyblue', alpha=0.7, edgecolor='black')
            
            ax2.set_yticks(y_positions)
            ax2.set_yticklabels([p['name'] for p in priorities])
            ax2.set_xlabel('우선순위 (낮을수록 높음)', fontsize=12)
            ax2.set_title('배치 우선순위', fontsize=14, fontweight='bold')
            ax2.invert_yaxis()
            ax2.grid(axis='x', alpha=0.3)
        
        plt.suptitle('공간 프로그램 다이어그램', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        return fig
    
    def figure_to_base64(self, fig: plt.Figure) -> str:
        """
        matplotlib Figure를 base64 문자열로 변환
        
        Args:
            fig: matplotlib Figure 객체
        
        Returns:
            base64 인코딩된 이미지 문자열
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64


class StoryboardVisualizer:
    """스토리보드 시각화 클래스"""
    
    def __init__(self):
        """초기화"""
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False
    
    def create_storyboard(self, scenes: List[Dict[str, Any]], 
                         title: str = "스토리보드") -> plt.Figure:
        """
        스토리보드 생성
        
        Args:
            scenes: 장면 정보 리스트 [{
                'scene_num': 1,
                'duration': '5초',
                'location': '기숙사',
                'camera': '와이드샷',
                'elements': '기상 장면',
                'narration': '새벽 6시...'
            }]
            title: 스토리보드 제목
        
        Returns:
            matplotlib Figure 객체
        """
        n_scenes = len(scenes)
        cols = min(3, n_scenes)
        rows = (n_scenes + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))
        if n_scenes == 1:
            axes = [axes]
        elif rows == 1:
            axes = axes if isinstance(axes, list) else [axes]
        else:
            axes = axes.flatten()
        
        for idx, scene in enumerate(scenes):
            ax = axes[idx] if idx < len(axes) else None
            if ax is None:
                break
            
            # 장면 프레임
            rect = FancyBboxPatch((0, 0), 1, 1,
                                boxstyle="round,pad=0.02",
                                facecolor='lightgray', alpha=0.3,
                                edgecolor='black', linewidth=2,
                                transform=ax.transAxes)
            ax.add_patch(rect)
            
            # 장면 정보 텍스트
            info_text = f"장면 {scene.get('scene_num', idx+1)}\n"
            info_text += f"시간: {scene.get('duration', 'N/A')}\n"
            info_text += f"장소: {scene.get('location', 'N/A')}\n"
            info_text += f"카메라: {scene.get('camera', 'N/A')}\n"
            info_text += f"\n요소: {scene.get('elements', 'N/A')}\n"
            info_text += f"\n내레이션:\n{scene.get('narration', 'N/A')}"
            
            ax.text(0.5, 0.5, info_text,
                   ha='center', va='center',
                   fontsize=9, transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
        
        # 빈 서브플롯 숨기기
        for idx in range(n_scenes, len(axes)):
            axes[idx].axis('off')
        
        plt.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        return fig
    
    def create_journey_map(self, journey_stages: List[Dict[str, Any]]) -> plt.Figure:
        """
        고객 여정 맵 생성
        
        Args:
            journey_stages: 여정 단계 리스트 [{
                'stage': '1단계: 사전 접촉',
                'touchpoints': [...],
                'services': [...],
                'spaces': [...]
            }]
        
        Returns:
            matplotlib Figure 객체
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        n_stages = len(journey_stages)
        stage_width = 1.0 / n_stages
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
        
        for i, stage in enumerate(journey_stages):
            x_center = (i + 0.5) * stage_width
            color = colors[i % len(colors)]
            
            # 단계 박스
            rect = FancyBboxPatch((x_center - stage_width*0.4, 0.7),
                                 stage_width*0.8, 0.25,
                                 boxstyle="round,pad=0.02",
                                 facecolor=color, alpha=0.7,
                                 edgecolor='black', linewidth=2,
                                 transform=ax.transAxes)
            ax.add_patch(rect)
            
            # 단계명
            ax.text(x_center, 0.825, stage.get('stage', f'단계 {i+1}'),
                   ha='center', va='center',
                   fontsize=12, fontweight='bold',
                   transform=ax.transAxes)
            
            # 터치포인트
            touchpoints = stage.get('touchpoints', [])
            y_pos = 0.6
            for tp in touchpoints[:3]:  # 최대 3개만 표시
                ax.text(x_center, y_pos, f"• {tp}",
                       ha='center', va='top',
                       fontsize=9, transform=ax.transAxes)
                y_pos -= 0.08
            
            # 서비스
            services = stage.get('services', [])
            y_pos = 0.35
            for svc in services[:2]:  # 최대 2개만 표시
                ax.text(x_center, y_pos, f"○ {svc}",
                       ha='center', va='top',
                       fontsize=8, transform=ax.transAxes)
                y_pos -= 0.06
            
            # 화살표 (다음 단계로)
            if i < n_stages - 1:
                arrow_x = (i + 1) * stage_width
                ax.annotate('', xy=(arrow_x - stage_width*0.1, 0.825),
                           xytext=(arrow_x - stage_width*0.9, 0.825),
                           arrowprops=dict(arrowstyle='->', lw=2, color='black'),
                           transform=ax.transAxes)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_title('고객 여정 맵', fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        return fig
    
    def figure_to_base64(self, fig: plt.Figure) -> str:
        """matplotlib Figure를 base64 문자열로 변환"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

