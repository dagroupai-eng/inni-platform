"""
시나리오 처리 모듈 - 시나리오 데이터 구조화 및 처리
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class ScenarioProcessor:
    """시나리오 데이터 처리 클래스"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def parse_persona_scenario(self, text: str) -> Dict[str, Any]:
        """
        페르소나 시나리오 텍스트 파싱
        
        Args:
            text: AI 분석 결과 텍스트
        
        Returns:
            구조화된 페르소나 시나리오 데이터
        """
        result = {
            'personas': [],
            'time_schedules': {},
            'activities': [],
            'space_scenarios': []
        }
        
        # 페르소나 추출
        persona_pattern = r'(엘리트 선수|유망주|지역주민|관광객|스카우트)'
        personas = re.findall(persona_pattern, text)
        result['personas'] = list(set(personas))
        
        # 시간대별 일과 추출
        time_patterns = [
            r'(오전\s*6-9시|새벽\s*6-9시).*?(?=오전\s*9-12시|오후)',
            r'(오전\s*9-12시).*?(?=오후\s*12-6시|저녁)',
            r'(오후\s*12-6시).*?(?=저녁\s*6-9시|야간)',
            r'(저녁\s*6-9시).*?(?=저녁\s*9-12시|야간)',
            r'(저녁\s*9-12시|야간).*?(?=오전|$)'
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                time_period = match.group(1)
                content = match.group(0)
                activities = self._extract_activities(content)
                result['time_schedules'][time_period] = activities
        
        # 주요 활동 추출
        activity_keywords = ['훈련', '수업', '식사', '재활', '휴식', '학습']
        for keyword in activity_keywords:
            if keyword in text:
                result['activities'].append(keyword)
        
        # 공간 활용 시나리오 추출
        scenario_pattern = r'시나리오\s*\d+[.:]\s*(.+?)(?=시나리오|$)'
        scenarios = re.findall(scenario_pattern, text, re.DOTALL)
        result['space_scenarios'] = scenarios[:5]  # 최대 5개
        
        return result
    
    def _extract_activities(self, text: str) -> List[str]:
        """활동 목록 추출"""
        activities = []
        activity_patterns = [
            r'(\d+:\d+).*?([가-힣]+(?:훈련|수업|식사|재활|휴식|학습))',
            r'([가-힣]+(?:훈련|수업|식사|재활|휴식|학습))'
        ]
        
        for pattern in activity_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                activity = match.group(0).strip()
                if activity and activity not in activities:
                    activities.append(activity)
        
        return activities[:10]  # 최대 10개
    
    def parse_masterplan_scenario(self, text: str) -> Dict[str, Any]:
        """
        마스터플랜 시나리오 텍스트 파싱
        
        Args:
            text: AI 분석 결과 텍스트
        
        Returns:
            구조화된 마스터플랜 시나리오 데이터
        """
        result = {
            'user_groups': [],
            'facility_utilization': {},
            'time_periods': {},
            'space_scenarios': [],
            'optimization_strategies': []
        }
        
        # 사용자 그룹 추출
        user_group_pattern = r'(엘리트 선수|유망주|감독|코치|지역주민|생활체육 이용자)'
        user_groups = re.findall(user_group_pattern, text)
        result['user_groups'] = list(set(user_groups))
        
        # 시설 이용률 추출
        facility_pattern = r'(테니스 코트|체육관|재활센터|컨벤션홀).*?(\d+%)'
        facility_matches = re.finditer(facility_pattern, text)
        for match in facility_matches:
            facility = match.group(1)
            utilization = match.group(2)
            result['facility_utilization'][facility] = utilization
        
        # 시간대별 시나리오 추출
        time_period_pattern = r'(오전\s*6-9시|오전\s*9-12시|오후\s*12-6시|저녁\s*6-9시|저녁\s*9-12시).*?:(.+?)(?=오전|오후|저녁|$)'
        time_matches = re.finditer(time_period_pattern, text, re.DOTALL)
        for match in time_matches:
            time_period = match.group(1)
            scenario = match.group(2).strip()
            result['time_periods'][time_period] = scenario
        
        # 최적화 전략 추출
        strategy_keywords = ['공간 전환', '유휴 공간', '다목적 활용', '시간대별']
        for keyword in strategy_keywords:
            if keyword in text:
                # 전략 문단 추출
                strategy_pattern = rf'{keyword}.*?[.:]\s*(.+?)(?=\n\n|$)'
                strategy_match = re.search(strategy_pattern, text, re.DOTALL)
                if strategy_match:
                    result['optimization_strategies'].append({
                        'keyword': keyword,
                        'description': strategy_match.group(1).strip()[:200]
                    })
        
        return result
    
    def parse_storyboard(self, text: str) -> List[Dict[str, Any]]:
        """
        스토리보드 텍스트 파싱
        
        Args:
            text: AI 분석 결과 텍스트
        
        Returns:
            구조화된 스토리보드 장면 리스트
        """
        scenes = []
        
        # 장면 번호 패턴
        scene_pattern = r'장면\s*(\d+)[.:]\s*(.+?)(?=장면\s*\d+|$)'
        scene_matches = re.finditer(scene_pattern, text, re.DOTALL)
        
        for match in scene_matches:
            scene_num = int(match.group(1))
            content = match.group(2)
            
            scene = {
                'scene_num': scene_num,
                'duration': self._extract_field(content, r'지속시간[:\s]*(\d+초|\d+분)'),
                'location': self._extract_field(content, r'장소[:\s]*([가-힣\s]+)'),
                'camera': self._extract_field(content, r'카메라[:\s]*([가-힣\s]+)'),
                'elements': self._extract_field(content, r'요소[:\s]*([가-힣\s]+)'),
                'narration': self._extract_field(content, r'내레이션[:\s]*([가-힣\s,.]+)')
            }
            
            # 기본값 설정
            if not scene['duration']:
                scene['duration'] = '5초'
            if not scene['location']:
                scene['location'] = 'N/A'
            if not scene['camera']:
                scene['camera'] = '와이드샷'
            if not scene['elements']:
                scene['elements'] = content[:50]
            if not scene['narration']:
                scene['narration'] = content[:100]
            
            scenes.append(scene)
        
        return scenes
    
    def _extract_field(self, text: str, pattern: str) -> Optional[str]:
        """필드 추출 헬퍼"""
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    
    def parse_business_model(self, text: str) -> Dict[str, Any]:
        """
        비즈니스 모델 텍스트 파싱
        
        Args:
            text: AI 분석 결과 텍스트
        
        Returns:
            구조화된 비즈니스 모델 데이터
        """
        result = {
            'associated_industries': [],
            'value_chain': {},
            'cluster_effects': [],
            'revenue_streams': []
        }
        
        # 연관 산업 추출
        industry_pattern = r'(1차|2차|3차)\s*산업[:\s]*([가-힣\s,]+)'
        industry_matches = re.finditer(industry_pattern, text)
        for match in industry_matches:
            level = match.group(1)
            industries = [i.strip() for i in match.group(2).split(',')]
            result['associated_industries'].append({
                'level': level,
                'industries': industries
            })
        
        # 수익원 추출
        revenue_pattern = r'(학비|기숙사비|전지훈련|호텔|컨벤션|재활|시설 대관|IP|라이선싱).*?(\d+[만억]?원|\d+[,\d]+원)'
        revenue_matches = re.finditer(revenue_pattern, text)
        for match in revenue_matches:
            stream = match.group(1)
            amount = match.group(2)
            result['revenue_streams'].append({
                'stream': stream,
                'amount': amount
            })
        
        return result
    
    def create_summary(self, scenario_data: Dict[str, Any], 
                      scenario_type: str) -> str:
        """
        시나리오 데이터 요약 생성
        
        Args:
            scenario_data: 구조화된 시나리오 데이터
            scenario_type: 시나리오 유형 ('persona', 'masterplan', 'storyboard', 'business')
        
        Returns:
            요약 텍스트
        """
        summary = f"## {scenario_type.upper()} 시나리오 요약\n\n"
        
        if scenario_type == 'persona':
            summary += f"**페르소나**: {', '.join(scenario_data.get('personas', []))}\n\n"
            summary += f"**주요 활동**: {', '.join(scenario_data.get('activities', []))}\n\n"
            summary += f"**시나리오 수**: {len(scenario_data.get('space_scenarios', []))}개\n"
        
        elif scenario_type == 'masterplan':
            summary += f"**사용자 그룹**: {', '.join(scenario_data.get('user_groups', []))}\n\n"
            summary += f"**시설 이용률**: {len(scenario_data.get('facility_utilization', {}))}개 시설\n\n"
            summary += f"**최적화 전략**: {len(scenario_data.get('optimization_strategies', []))}개\n"
        
        elif scenario_type == 'storyboard':
            summary += f"**총 장면 수**: {len(scenario_data)}개\n\n"
            if scenario_data:
                total_duration = sum([int(s.get('duration', '5초').replace('초', '').replace('분', '00')) 
                                    for s in scenario_data if s.get('duration')])
                summary += f"**예상 총 시간**: 약 {total_duration}초\n"
        
        elif scenario_type == 'business':
            summary += f"**연관 산업**: {len(scenario_data.get('associated_industries', []))}개 분류\n\n"
            summary += f"**수익원**: {len(scenario_data.get('revenue_streams', []))}개\n"
        
        return summary

