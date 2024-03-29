import os
from time import strftime, gmtime

from src.utils.logging.callbacks.config_logger import ConfigLogger
from src.utils.logging.callbacks.csv_logger import CsvLogger
from src.utils.logging.callbacks.csv_plotter import CsvPlotter
from src.utils.logging.callbacks.model_saver import ModelSaver
from src.utils.settings import Settings


class CallbackBuilder():

    def __init__(self, model, callback_classes):
        super().__init__()

        self.model = model
        self.callback_classes = callback_classes

        self.active_callbacks = []

    def __call__(self):
        timestamp = strftime("%Y-%m-%d-%H-%M-%S", gmtime())
        settings = Settings()
        log_path = '{}/{}_{}'.format(settings.get_training_root_dir(), self.model.name, timestamp)
        os.makedirs(log_path, exist_ok=True)

        if CsvLogger in self.callback_classes:
            csv_logger = CsvLogger(self.model.name, log_path)
            self.active_callbacks.append(csv_logger)

        if CsvPlotter in self.callback_classes:
            assert CsvLogger in self.callback_classes

            plotter = CsvPlotter(self.model, log_path)
            self.active_callbacks.append(plotter)

        if ConfigLogger in self.callback_classes:
            config_logger = ConfigLogger(self.model, log_path)
            self.active_callbacks.append(config_logger)

        if ModelSaver in self.callback_classes:
            model_saver = ModelSaver(self.model, log_path)
            self.active_callbacks.append(model_saver)

        return self.active_callbacks
