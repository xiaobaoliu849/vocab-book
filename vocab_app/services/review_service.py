from datetime import datetime, timedelta

class ReviewService:
    @staticmethod
    def calculate_sm2(quality, word_data):
        """
        SM-2 Algorithm
        quality: 0-5
        word_data: dict
        Returns: (easiness, interval, repetitions)
        """
        easiness = word_data.get('easiness') or 2.5
        interval = word_data.get('interval') or 0
        repetitions = word_data.get('repetitions') or 0

        # Compatibility with old stage-based data
        if repetitions == 0 and word_data.get('stage', 0) > 0:
            repetitions = word_data['stage']
            stage = word_data['stage']
            stage_intervals = [1, 2, 4, 7, 15, 30]
            interval = stage_intervals[min(5, stage-1)] if stage <= 6 else 30

        # 1. Update Easiness Factor
        if quality >= 3:
            easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        if easiness < 1.3:
            easiness = 1.3

        # 2. Update Repetitions and Interval
        if quality < 3:
            repetitions = 0
            interval = 1
        else:
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = int(interval * easiness)

            repetitions += 1

        return easiness, interval, repetitions

    @staticmethod
    def calculate_next_review_time(interval):
        return (datetime.now() + timedelta(days=interval)).timestamp()

    @staticmethod
    def calculate_simple_stage(ok, current_stage):
        """
        Simple fixed interval algorithm (for spelling mode)
        Returns: (new_stage, next_ts, mastered)
        """
        INTERVALS = [1, 2, 4, 7, 15, 30]

        if ok:
            if current_stage < len(INTERVALS):
                days = INTERVALS[current_stage]
                next_ts = (datetime.now() + timedelta(days=days)).timestamp()
                new_stage = current_stage + 1
                mastered = False
            else:
                next_ts = 0
                new_stage = current_stage + 1
                mastered = True
        else:
            new_stage = 0
            next_ts = 0
            mastered = False

        return new_stage, next_ts, mastered
